# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Independent free-flight camera controller for the native map renderer."""

from __future__ import annotations

from dataclasses import dataclass, replace
import math
import threading
import time
from collections.abc import Callable

from protocols.map_renderer.map_renderer_client import MapRendererClient

EARTH_RADIUS_M = 6_371_000.0


@dataclass(frozen=True)
class FlightState:
    """Current virtual aircraft state used to drive the map camera."""

    latitude_deg: float
    longitude_deg: float
    heading_deg: float = 0.0
    pitch_deg: float = 55.0
    zoom: float = 14.0
    speed_mps: float = 0.0


class FlightCameraController:
    """Integrate a virtual aircraft position and exclusively drive flight presentation.

    Keyboard input changes commanded targets. The rendered aircraft eases toward
    those targets instead of snapping immediately, which gives the map camera the
    inertia expected from an aircraft rather than a cursor.
    """

    def __init__(
        self,
        map_renderer: MapRendererClient,
        initial_state: FlightState,
        *,
        frame_rate_hz: float = 30.0,
        max_acceleration_mps2: float = 7.0,
        max_turn_rate_deg_s: float = 20.0,
        max_pitch_rate_deg_s: float = 12.0,
        max_zoom_rate_s: float = 1.25,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if frame_rate_hz <= 0.0:
            raise ValueError("frame_rate_hz must be greater than zero")
        self._map_renderer = map_renderer
        self._state = self._normalized(initial_state)
        self._target_state = self._state
        self._frame_period_s = 1.0 / frame_rate_hz
        self._max_acceleration_mps2 = max_acceleration_mps2
        self._max_turn_rate_deg_s = max_turn_rate_deg_s
        self._max_pitch_rate_deg_s = max_pitch_rate_deg_s
        self._max_zoom_rate_s = max_zoom_rate_s
        self._clock = clock
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_frame_time: float | None = None

    @property
    def state(self) -> FlightState:
        with self._lock:
            return self._state

    @property
    def target_state(self) -> FlightState:
        with self._lock:
            return self._target_state

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if self.is_running:
            return
        self._stop_event.clear()
        self._last_frame_time = self._clock()
        self._map_renderer.set_flight_mode(True)
        self.render_once(self._last_frame_time)
        self._thread = threading.Thread(target=self._run, name="FlightCameraController", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None and self._thread.is_alive() and self._thread is not threading.current_thread():
            self._thread.join(timeout=1.0)
        self._thread = None
        self._map_renderer.set_flight_mode(False)

    def adjust(
        self,
        *,
        speed_delta_mps: float = 0.0,
        heading_delta_deg: float = 0.0,
        pitch_delta_deg: float = 0.0,
        zoom_delta: float = 0.0,
    ) -> FlightState:
        """Adjust commanded flight targets and return the new target state."""
        with self._lock:
            self._target_state = self._normalized(replace(
                self._target_state,
                speed_mps=self._target_state.speed_mps + speed_delta_mps,
                heading_deg=self._target_state.heading_deg + heading_delta_deg,
                pitch_deg=self._target_state.pitch_deg + pitch_delta_deg,
                zoom=self._target_state.zoom + zoom_delta,
            ))
            return self._target_state

    def render_once(self, now: float | None = None) -> FlightState:
        current_time = self._clock() if now is None else now
        with self._lock:
            previous = self._last_frame_time
            elapsed = 0.0 if previous is None else max(0.0, current_time - previous)
            self._last_frame_time = current_time
            state = self._state
            target = self._target_state

            if elapsed > 0.0:
                speed = _approach(state.speed_mps, target.speed_mps, self._max_acceleration_mps2 * elapsed)
                heading = _approach_heading(state.heading_deg, target.heading_deg, self._max_turn_rate_deg_s * elapsed)
                pitch = _approach(state.pitch_deg, target.pitch_deg, self._max_pitch_rate_deg_s * elapsed)
                zoom = _approach(state.zoom, target.zoom, self._max_zoom_rate_s * elapsed)

                latitude = state.latitude_deg
                longitude = state.longitude_deg
                if speed > 0.0:
                    latitude, longitude = _project_position(
                        latitude,
                        longitude,
                        speed * elapsed,
                        heading,
                    )

                state = self._normalized(replace(
                    state,
                    latitude_deg=latitude,
                    longitude_deg=longitude,
                    speed_mps=speed,
                    heading_deg=heading,
                    pitch_deg=pitch,
                    zoom=zoom,
                ))
                self._state = state

        self._map_renderer.set_flight_state(
            latitude=state.latitude_deg,
            longitude=state.longitude_deg,
            zoom=state.zoom,
            bearing=state.heading_deg,
            pitch=state.pitch_deg,
        )
        return state

    def _run(self) -> None:
        while not self._stop_event.wait(self._frame_period_s):
            self.render_once()

    @staticmethod
    def _normalized(state: FlightState) -> FlightState:
        return replace(
            state,
            latitude_deg=min(85.0, max(-85.0, state.latitude_deg)),
            longitude_deg=((state.longitude_deg + 180.0) % 360.0) - 180.0,
            heading_deg=state.heading_deg % 360.0,
            # MapLibre Native's default camera constraint tops out at 60 degrees.
            pitch_deg=min(60.0, max(0.0, state.pitch_deg)),
            zoom=min(19.0, max(3.0, state.zoom)),
            speed_mps=max(0.0, state.speed_mps),
        )


def _approach(value: float, target: float, maximum_delta: float) -> float:
    if value < target:
        return min(target, value + maximum_delta)
    return max(target, value - maximum_delta)


def _approach_heading(value: float, target: float, maximum_delta: float) -> float:
    difference = ((target - value + 180.0) % 360.0) - 180.0
    if abs(difference) <= maximum_delta:
        return target % 360.0
    return (value + math.copysign(maximum_delta, difference)) % 360.0


def _project_position(latitude: float, longitude: float, distance_m: float, bearing_deg: float) -> tuple[float, float]:
    angular_distance = distance_m / EARTH_RADIUS_M
    bearing = math.radians(bearing_deg)
    latitude_radians = math.radians(latitude)
    longitude_radians = math.radians(longitude)
    projected_latitude = math.asin(
        math.sin(latitude_radians) * math.cos(angular_distance)
        + math.cos(latitude_radians) * math.sin(angular_distance) * math.cos(bearing)
    )
    projected_longitude = longitude_radians + math.atan2(
        math.sin(bearing) * math.sin(angular_distance) * math.cos(latitude_radians),
        math.cos(angular_distance) - math.sin(latitude_radians) * math.sin(projected_latitude),
    )
    return math.degrees(projected_latitude), ((math.degrees(projected_longitude) + 180.0) % 360.0) - 180.0
