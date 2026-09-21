# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Simulated geographic position source for navigation development."""

from __future__ import annotations

import math
import threading

from controllers.navigation.navigation_state import PositionState
from controllers.navigation.position_source_if import PositionSourceIf, PositionStateCallback
from controllers.navigation.route_simulation_if import RouteSimulationIf
from controllers.route_planning.route_planning_types import GeoPoint, RouteResult

_EARTH_RADIUS_M = 6371008.8


class SimulatedPositionSource(PositionSourceIf, RouteSimulationIf):
    """Publish deterministic geographic position updates without a receiver."""

    def __init__(
        self,
        profile: str = "driving",
        latitude_deg: float = 42.8028,
        longitude_deg: float = -83.0127,
        speed_mps: float = 13.4,
        course_deg: float = 180.0,
        update_rate_hz: float = 5.0,
    ) -> None:
        if update_rate_hz <= 0:
            raise ValueError("update_rate_hz must be greater than zero")
        self._profile = profile.strip().lower()
        self._latitude_deg = latitude_deg
        self._longitude_deg = longitude_deg
        # Retained temporarily for runtime-config compatibility while simulated
        # ground motion moves to its own source.
        self._speed_mps = speed_mps
        self._course_deg = course_deg
        self._period_s = 1.0 / update_rate_hz
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._route_lock = threading.Lock()
        self._route_shape: tuple[GeoPoint, ...] | None = None
        self._route_segment_lengths_m: tuple[float, ...] = ()
        self._route_progress_m = 0.0
        self._route_total_m = 0.0
        self._route_speed_mps = 0.0

    def start(self, callback: PositionStateCallback) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            args=(callback,),
            name="simulated-position",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=max(1.0, self._period_s * 2.0))
        self._thread = None

    def follow_route(self, route: RouteResult, *, time_scale: float = 60.0) -> None:
        """Drive simulated position along a calculated route shape."""
        if time_scale <= 0.0:
            raise ValueError("time_scale must be greater than zero")
        if len(route.shape) < 2:
            raise ValueError("route shape must contain at least two points")

        segment_lengths = tuple(
            self._distance_m(start, end)
            for start, end in zip(route.shape, route.shape[1:])
        )
        total_m = sum(segment_lengths)
        if total_m <= 0.0:
            raise ValueError("route shape must have nonzero length")

        simulated_duration_s = max(self._period_s, route.duration_seconds / time_scale)
        with self._route_lock:
            self._route_shape = tuple(route.shape)
            self._route_segment_lengths_m = segment_lengths
            self._route_progress_m = 0.0
            self._route_total_m = total_m
            self._route_speed_mps = total_m / simulated_duration_s

    def stop_route(self) -> None:
        """Return to the configured free-running simulation profile."""
        with self._route_lock:
            self._route_shape = None
            self._route_segment_lengths_m = ()
            self._route_progress_m = 0.0
            self._route_total_m = 0.0
            self._route_speed_mps = 0.0

    def _run(self, callback: PositionStateCallback) -> None:
        phase = 0.0
        while not self._stop_event.is_set():
            route_state = self._route_state()
            if route_state is not None:
                latitude, longitude, speed_mps, course_deg = route_state
                source = "route-simulation"
            else:
                if self._profile == "stationary":
                    latitude = self._latitude_deg
                    longitude = self._longitude_deg
                elif self._profile == "driving":
                    phase += 0.04
                    latitude = self._latitude_deg + 0.002 * math.sin(phase)
                    longitude = self._longitude_deg + 0.002 * math.cos(phase)
                else:
                    raise ValueError(f"unsupported simulated GPS profile: {self._profile}")
                speed_mps = self._speed_mps + 1.5 * math.sin(phase)
                course_deg = self._course_deg
                source = "simulation"

            callback(PositionState(
                latitude_deg=latitude,
                longitude_deg=longitude,
                altitude_m=180.0 + 8.0 * math.sin(phase * 0.5),
                speed_mps=speed_mps,
                course_deg=course_deg,
                fix_mode=3,
                satellites_visible=12,
                satellites_used=9,
                accuracy_m=3.0,
                source=source,
            ))
            self._stop_event.wait(self._period_s)

    def _route_state(self) -> tuple[float, float, float, float] | None:
        with self._route_lock:
            shape = self._route_shape
            if shape is None:
                return None

            progress_m = min(self._route_progress_m, self._route_total_m)
            segment_index, fraction = self._segment_for_progress(progress_m)
            start = shape[segment_index]
            end = shape[segment_index + 1]
            latitude = start.latitude + fraction * (end.latitude - start.latitude)
            longitude = start.longitude + fraction * (end.longitude - start.longitude)
            course_deg = self._bearing_deg(start, end)
            speed_mps = 0.0 if progress_m >= self._route_total_m else self._route_speed_mps
            self._route_progress_m = min(
                self._route_total_m,
                self._route_progress_m + self._route_speed_mps * self._period_s,
            )
            return latitude, longitude, speed_mps, course_deg

    def _segment_for_progress(self, progress_m: float) -> tuple[int, float]:
        remaining = progress_m
        lengths = self._route_segment_lengths_m
        for index, length_m in enumerate(lengths):
            if remaining <= length_m or index == len(lengths) - 1:
                fraction = 0.0 if length_m <= 0.0 else min(1.0, remaining / length_m)
                return index, fraction
            remaining -= length_m
        return len(lengths) - 1, 1.0

    @staticmethod
    def _distance_m(first: GeoPoint, second: GeoPoint) -> float:
        lat1 = math.radians(first.latitude)
        lat2 = math.radians(second.latitude)
        delta_lat = lat2 - lat1
        delta_lon = math.radians(second.longitude - first.longitude)
        value = (
            math.sin(delta_lat / 2.0) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2.0) ** 2
        )
        return 2.0 * _EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(value)))

    @staticmethod
    def _bearing_deg(first: GeoPoint, second: GeoPoint) -> float:
        lat1 = math.radians(first.latitude)
        lat2 = math.radians(second.latitude)
        delta_lon = math.radians(second.longitude - first.longitude)
        y = math.sin(delta_lon) * math.cos(lat2)
        x = (
            math.cos(lat1) * math.sin(lat2)
            - math.sin(lat1) * math.cos(lat2) * math.cos(delta_lon)
        )
        return (math.degrees(math.atan2(y, x)) + 360.0) % 360.0
