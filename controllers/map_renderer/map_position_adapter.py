"""Adapt normalized position and ground-motion reports to smooth map commands."""

from __future__ import annotations

import logging
import math
import threading
import time
from collections.abc import Callable

from controllers.navigation.navigation_state import GroundMotionState, PositionState
from protocols.map_renderer.map_renderer_client import (
    MapRendererClient,
    MapRendererUnavailableError,
)


LOGGER = logging.getLogger(__name__)
EARTH_RADIUS_M = 6_371_000.0


class MapPositionAdapter:
    """Smooth live position fixes and manage the navigation camera."""

    def __init__(
        self,
        map_renderer: MapRendererClient,
        *,
        follow: bool = True,
        zoom: float = 16.5,
        pitch: float = 45.0,
        frame_rate_hz: float = 30.0,
        correction_time_s: float = 0.5,
        maximum_prediction_age_s: float = 1.5,
        snap_distance_m: float = 75.0,
        minimum_camera_interval_s: float = 0.10,
        minimum_course_speed_mps: float = 1.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        for name, value in {
            "frame_rate_hz": frame_rate_hz,
            "correction_time_s": correction_time_s,
            "maximum_prediction_age_s": maximum_prediction_age_s,
            "snap_distance_m": snap_distance_m,
        }.items():
            if value <= 0.0:
                raise ValueError(f"{name} must be greater than zero")
        if minimum_camera_interval_s < 0.0:
            raise ValueError("minimum_camera_interval_s must not be negative")
        if minimum_course_speed_mps < 0.0:
            raise ValueError("minimum_course_speed_mps must not be negative")

        self._map_renderer = map_renderer
        self._follow = follow
        self._zoom = zoom
        self._pitch = pitch
        self._frame_period_s = 1.0 / frame_rate_hz
        self._correction_time_s = correction_time_s
        self._maximum_prediction_age_s = maximum_prediction_age_s
        self._snap_distance_m = snap_distance_m
        self._minimum_camera_interval_s = minimum_camera_interval_s
        self._minimum_course_speed_mps = minimum_course_speed_mps
        self._clock = clock

        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._latest_fix: PositionState | None = None
        self._latest_fix_time: float | None = None
        self._ground_motion: GroundMotionState | None = None
        self._display_position: tuple[float, float] | None = None
        self._last_frame_time: float | None = None
        self._last_camera_update: float | None = None
        self._bearing = 0.0
        self._manual_camera: tuple[float, float, float] | None = None

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def is_manual_camera(self) -> bool:
        with self._lock:
            return self._manual_camera is not None

    def start(self) -> None:
        if self.is_running:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="MapPositionAdapter",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if (
            self._thread is not None
            and self._thread.is_alive()
            and self._thread is not threading.current_thread()
        ):
            self._thread.join(timeout=1.0)
        self._thread = None

    def update(self, state: PositionState) -> None:
        """Accept one authoritative position fix."""
        if (
            not state.has_fix
            or state.latitude_deg is None
            or state.longitude_deg is None
        ):
            return

        now = self._clock()
        first_fix = False
        with self._lock:
            self._latest_fix = state
            self._latest_fix_time = now
            if self._display_position is None:
                self._display_position = (state.latitude_deg, state.longitude_deg)
                self._last_frame_time = now
                self._apply_motion_bearing_locked()
                first_fix = True

        if first_fix:
            self.render_once(now)

    def update_ground_motion(self, state: GroundMotionState) -> None:
        """Accept independent ground speed and course information."""
        with self._lock:
            self._ground_motion = state
            self._apply_motion_bearing_locked()

    def adjust_camera(
        self,
        *,
        zoom_delta: float = 0.0,
        pitch_delta: float = 0.0,
        bearing_delta: float = 0.0,
    ) -> tuple[float, float, float]:
        """Adjust the followed camera and enter manual camera mode."""
        with self._lock:
            if self._manual_camera is None:
                zoom = self._adaptive_zoom_locked()
                pitch = self._pitch
                bearing = self._bearing
            else:
                zoom, pitch, bearing = self._manual_camera

            zoom = min(19.0, max(3.0, zoom + zoom_delta))
            pitch = min(60.0, max(0.0, pitch + pitch_delta))
            bearing = (bearing + bearing_delta) % 360.0
            self._manual_camera = (zoom, pitch, bearing)
            self._last_camera_update = None
            return self._manual_camera

    def enable_auto_camera(self) -> None:
        """Return zoom, pitch, and bearing to automatic navigation behavior."""
        with self._lock:
            self._manual_camera = None
            self._last_camera_update = None

    def render_once(self, now: float | None = None) -> None:
        current_time = self._clock() if now is None else now
        with self._lock:
            frame = self._calculate_frame(current_time)
            if frame is None:
                return
            latitude, longitude, bearing, update_camera = frame
            zoom, pitch, camera_bearing = self._camera_parameters_locked(bearing)

        try:
            self._map_renderer.set_position(latitude, longitude)
            if self._follow and update_camera:
                self._map_renderer.set_camera(
                    latitude=latitude,
                    longitude=longitude,
                    zoom=zoom,
                    bearing=camera_bearing,
                    pitch=pitch,
                )
        except MapRendererUnavailableError as error:
            LOGGER.warning("%s", error)

    def _run(self) -> None:
        while not self._stop_event.wait(self._frame_period_s):
            self.render_once()

    def _calculate_frame(
        self,
        now: float,
    ) -> tuple[float, float, float, bool] | None:
        fix = self._latest_fix
        fix_time = self._latest_fix_time
        display = self._display_position
        if fix is None or fix_time is None or display is None:
            return None

        elapsed = max(0.0, now - fix_time)
        prediction_age = min(elapsed, self._maximum_prediction_age_s)
        target = (fix.latitude_deg, fix.longitude_deg)
        assert target[0] is not None and target[1] is not None

        motion = self._ground_motion
        moving = (
            motion is not None
            and motion.speed_mps is not None
            and motion.speed_mps >= self._minimum_course_speed_mps
            and motion.course_deg is not None
        )
        if moving:
            target = _project_position(
                target[0],
                target[1],
                motion.speed_mps * prediction_age,
                motion.course_deg,
            )

        frame_delta = (
            self._frame_period_s
            if self._last_frame_time is None
            else max(0.0, now - self._last_frame_time)
        )
        error_m = _distance_m(display, target)
        if error_m >= self._snap_distance_m:
            display = target
        else:
            alpha = 1.0 - math.exp(-frame_delta / self._correction_time_s)
            display = (
                display[0] + alpha * (target[0] - display[0]),
                display[1] + alpha * (target[1] - display[1]),
            )

        if moving:
            self._bearing = _smooth_bearing(
                self._bearing,
                motion.course_deg,
                1.0 - math.exp(-frame_delta / self._correction_time_s),
            )

        update_camera = (
            self._last_camera_update is None
            or now - self._last_camera_update >= self._minimum_camera_interval_s
        )
        if update_camera:
            self._last_camera_update = now
        self._display_position = display
        self._last_frame_time = now
        return display[0], display[1], self._bearing, update_camera

    def _camera_parameters_locked(
        self,
        automatic_bearing: float,
    ) -> tuple[float, float, float]:
        if self._manual_camera is not None:
            return self._manual_camera
        return self._adaptive_zoom_locked(), self._pitch, automatic_bearing

    def _adaptive_zoom_locked(self) -> float:
        motion = self._ground_motion
        if motion is None or motion.speed_mps is None:
            return self._zoom

        speed = max(0.0, motion.speed_mps)
        if speed <= 3.0:
            return self._zoom
        if speed <= 13.5:
            return _interpolate(speed, 3.0, 13.5, self._zoom, 15.2)
        if speed <= 27.0:
            return _interpolate(speed, 13.5, 27.0, 15.2, 14.0)
        if speed <= 36.0:
            return _interpolate(speed, 27.0, 36.0, 14.0, 13.5)
        return 13.5

    def _apply_motion_bearing_locked(self) -> None:
        motion = self._ground_motion
        if (
            motion is not None
            and motion.course_deg is not None
            and motion.speed_mps is not None
            and motion.speed_mps >= self._minimum_course_speed_mps
        ):
            self._bearing = motion.course_deg % 360.0


def _interpolate(
    value: float,
    input_minimum: float,
    input_maximum: float,
    output_minimum: float,
    output_maximum: float,
) -> float:
    fraction = (value - input_minimum) / (input_maximum - input_minimum)
    return output_minimum + fraction * (output_maximum - output_minimum)


def _project_position(
    latitude: float,
    longitude: float,
    distance_m: float,
    bearing_deg: float,
) -> tuple[float, float]:
    angular_distance = distance_m / EARTH_RADIUS_M
    bearing = math.radians(bearing_deg)
    latitude_radians = math.radians(latitude)
    longitude_radians = math.radians(longitude)
    projected_latitude = math.asin(
        math.sin(latitude_radians) * math.cos(angular_distance)
        + math.cos(latitude_radians)
        * math.sin(angular_distance)
        * math.cos(bearing)
    )
    projected_longitude = longitude_radians + math.atan2(
        math.sin(bearing)
        * math.sin(angular_distance)
        * math.cos(latitude_radians),
        math.cos(angular_distance)
        - math.sin(latitude_radians) * math.sin(projected_latitude),
    )
    return math.degrees(projected_latitude), math.degrees(projected_longitude)


def _distance_m(
    first: tuple[float, float],
    second: tuple[float, float],
) -> float:
    latitude_delta = math.radians(second[0] - first[0])
    longitude_delta = math.radians(second[1] - first[1])
    latitude_1 = math.radians(first[0])
    latitude_2 = math.radians(second[0])
    haversine = (
        math.sin(latitude_delta / 2.0) ** 2
        + math.cos(latitude_1)
        * math.cos(latitude_2)
        * math.sin(longitude_delta / 2.0) ** 2
    )
    return 2.0 * EARTH_RADIUS_M * math.asin(math.sqrt(min(1.0, haversine)))


def _smooth_bearing(current: float, target: float, alpha: float) -> float:
    difference = (target - current + 180.0) % 360.0 - 180.0
    return (current + alpha * difference) % 360.0
