"""Adapt normalized position reports to smooth map-renderer commands."""

from __future__ import annotations

import logging
import math
import threading
import time
from collections.abc import Callable

from controllers.navigation.navigation_state import PositionState
from protocols.map_renderer.map_renderer_client import (
    MapRendererClient,
    MapRendererUnavailableError,
)


LOGGER = logging.getLogger(__name__)
EARTH_RADIUS_M = 6_371_000.0


class MapPositionAdapter:
    """Smooth live position fixes into marker and follow-camera commands."""

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
        minimum_camera_interval_s: float = 0.05,
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
        self._display_position: tuple[float, float] | None = None
        self._last_frame_time: float | None = None
        self._last_camera_update: float | None = None
        self._bearing = 0.0

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        """Start the display interpolation loop."""
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
        """Stop the interpolation loop."""
        self._stop_event.set()
        if (
            self._thread is not None
            and self._thread.is_alive()
            and self._thread is not threading.current_thread()
        ):
            self._thread.join(timeout=1.0)
        self._thread = None

    def update(self, state: PositionState) -> None:
        """Accept one authoritative GPS fix without altering it."""
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
                self._display_position = (
                    state.latitude_deg,
                    state.longitude_deg,
                )
                self._last_frame_time = now
                if (
                    state.course_deg is not None
                    and state.speed_mps is not None
                    and state.speed_mps >= self._minimum_course_speed_mps
                ):
                    self._bearing = state.course_deg % 360.0
                first_fix = True

        # Do not leave the map blank while waiting for the first timer tick.
        if first_fix:
            self.render_once(now)

    def render_once(self, now: float | None = None) -> None:
        """Advance and render one frame; public for deterministic testing."""
        current_time = self._clock() if now is None else now
        with self._lock:
            frame = self._calculate_frame(current_time)
        if frame is None:
            return

        latitude, longitude, bearing, update_camera = frame
        try:
            self._map_renderer.set_position(latitude, longitude)
            if self._follow and update_camera:
                self._map_renderer.set_camera(
                    latitude=latitude,
                    longitude=longitude,
                    zoom=self._zoom,
                    bearing=bearing,
                    pitch=self._pitch,
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

        moving = (
            fix.speed_mps is not None
            and fix.speed_mps >= self._minimum_course_speed_mps
            and fix.course_deg is not None
        )
        if moving:
            target = _project_position(
                target[0],
                target[1],
                fix.speed_mps * prediction_age,
                fix.course_deg,
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
                fix.course_deg,
                1.0 - math.exp(-frame_delta / self._correction_time_s),
            )

        update_camera = (
            self._last_camera_update is None
            or now - self._last_camera_update
            >= self._minimum_camera_interval_s
        )
        if update_camera:
            self._last_camera_update = now
        self._display_position = display
        self._last_frame_time = now
        return display[0], display[1], self._bearing, update_camera


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
    return 2.0 * EARTH_RADIUS_M * math.asin(
        math.sqrt(min(1.0, haversine))
    )


def _smooth_bearing(current: float, target: float, alpha: float) -> float:
    difference = (target - current + 180.0) % 360.0 - 180.0
    return (current + alpha * difference) % 360.0
