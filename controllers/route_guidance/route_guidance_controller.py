# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Route progress and maneuver guidance independent of position transport."""

from __future__ import annotations

import math
from dataclasses import dataclass

from controllers.route_planning.route_planning_types import GeoPoint, RouteResult
from .route_guidance_types import RouteGuidanceState

_EARTH_RADIUS_MILES = 3958.7613
_PROGRESS_EPSILON_MILES = 1e-6


@dataclass(frozen=True, slots=True)
class _Projection:
    segment_index: int
    segment_fraction: float
    distance_from_route_miles: float
    distance_along_route_miles: float


class RouteGuidanceController:
    """Track progress along one calculated route."""

    def __init__(
        self,
        route: RouteResult,
        *,
        off_route_threshold_miles: float = 0.05,
        on_route_threshold_miles: float | None = None,
        arrival_threshold_miles: float = 0.03,
    ) -> None:
        if off_route_threshold_miles <= 0.0:
            raise ValueError("off_route_threshold_miles must be positive")
        if arrival_threshold_miles <= 0.0:
            raise ValueError("arrival_threshold_miles must be positive")

        if on_route_threshold_miles is None:
            on_route_threshold_miles = off_route_threshold_miles * 0.6
        if on_route_threshold_miles <= 0.0:
            raise ValueError("on_route_threshold_miles must be positive")
        if on_route_threshold_miles > off_route_threshold_miles:
            raise ValueError(
                "on_route_threshold_miles must not exceed off_route_threshold_miles"
            )

        self._off_route_threshold_miles = off_route_threshold_miles
        self._on_route_threshold_miles = on_route_threshold_miles
        self._arrival_threshold_miles = arrival_threshold_miles
        self._route: RouteResult
        self._cumulative: tuple[float, ...]
        self._shape_distance_miles: float
        self._furthest_progress_miles: float
        self._off_route: bool
        self.replace_route(route)

    def replace_route(self, route: RouteResult) -> None:
        """Replace the active route and reset route-relative guidance state."""
        if len(route.shape) < 2:
            raise ValueError("route shape must contain at least two points")

        self._route = route
        self._cumulative = self._build_cumulative_distances(route.shape)
        self._shape_distance_miles = self._cumulative[-1]
        self._furthest_progress_miles = 0.0
        self._off_route = False

    def update(self, position: GeoPoint) -> RouteGuidanceState:
        """Update guidance using the latest geographic position."""
        projection = self._project_to_route(position)
        progress = max(
            self._furthest_progress_miles,
            projection.distance_along_route_miles,
        )
        self._furthest_progress_miles = progress

        remaining = max(0.0, self._shape_distance_miles - progress)
        destination_distance = self._distance_miles(position, self._route.shape[-1])
        route_complete = destination_distance <= self._arrival_threshold_miles
        self._off_route = self._update_off_route_state(
            projection.distance_from_route_miles,
            route_complete=route_complete,
        )

        maneuver_index = self._maneuver_index_for_progress(progress)
        maneuver = (
            None
            if maneuver_index is None
            else self._route.maneuvers[maneuver_index]
        )
        distance_to_maneuver = (
            None
            if maneuver is None
            else max(
                0.0,
                self._distance_at_shape_index(maneuver.end_shape_index) - progress,
            )
        )

        return RouteGuidanceState(
            distance_along_route_miles=progress,
            distance_remaining_miles=remaining,
            distance_from_route_miles=projection.distance_from_route_miles,
            current_maneuver_index=maneuver_index,
            current_maneuver=maneuver,
            distance_to_maneuver_miles=distance_to_maneuver,
            off_route=self._off_route,
            route_complete=route_complete,
        )

    def _update_off_route_state(
        self,
        distance_from_route_miles: float,
        *,
        route_complete: bool,
    ) -> bool:
        if route_complete:
            return False
        if self._off_route:
            return distance_from_route_miles > self._on_route_threshold_miles
        return distance_from_route_miles > self._off_route_threshold_miles

    def _maneuver_index_for_progress(self, progress: float) -> int | None:
        """Return the maneuver whose shape interval contains progress."""
        if not self._route.maneuvers:
            return None

        for index, maneuver in enumerate(self._route.maneuvers):
            end_distance = self._distance_at_shape_index(maneuver.end_shape_index)
            is_last = index == len(self._route.maneuvers) - 1
            if is_last or progress < end_distance - _PROGRESS_EPSILON_MILES:
                return index

        return len(self._route.maneuvers) - 1

    def _distance_at_shape_index(self, index: int) -> float:
        if index <= 0:
            return 0.0
        if index >= len(self._cumulative):
            return self._shape_distance_miles
        return self._cumulative[index]

    def _project_to_route(self, point: GeoPoint) -> _Projection:
        best: _Projection | None = None
        for index in range(len(self._route.shape) - 1):
            start = self._route.shape[index]
            end = self._route.shape[index + 1]
            fraction, distance = self._project_to_segment(point, start, end)
            segment_length = self._cumulative[index + 1] - self._cumulative[index]
            candidate = _Projection(
                segment_index=index,
                segment_fraction=fraction,
                distance_from_route_miles=distance,
                distance_along_route_miles=(
                    self._cumulative[index] + fraction * segment_length
                ),
            )
            if best is None or candidate.distance_from_route_miles < best.distance_from_route_miles:
                best = candidate
        assert best is not None
        return best

    @staticmethod
    def _project_to_segment(
        point: GeoPoint,
        start: GeoPoint,
        end: GeoPoint,
    ) -> tuple[float, float]:
        reference_lat = math.radians(
            (point.latitude + start.latitude + end.latitude) / 3.0
        )
        miles_per_lat_degree = math.pi * _EARTH_RADIUS_MILES / 180.0
        miles_per_lon_degree = miles_per_lat_degree * math.cos(reference_lat)

        ax = start.longitude * miles_per_lon_degree
        ay = start.latitude * miles_per_lat_degree
        bx = end.longitude * miles_per_lon_degree
        by = end.latitude * miles_per_lat_degree
        px = point.longitude * miles_per_lon_degree
        py = point.latitude * miles_per_lat_degree

        dx = bx - ax
        dy = by - ay
        length_squared = dx * dx + dy * dy
        if length_squared == 0.0:
            return 0.0, math.hypot(px - ax, py - ay)

        fraction = ((px - ax) * dx + (py - ay) * dy) / length_squared
        fraction = min(1.0, max(0.0, fraction))
        nearest_x = ax + fraction * dx
        nearest_y = ay + fraction * dy
        return fraction, math.hypot(px - nearest_x, py - nearest_y)

    @staticmethod
    def _build_cumulative_distances(shape: tuple[GeoPoint, ...]) -> tuple[float, ...]:
        distances = [0.0]
        for start, end in zip(shape, shape[1:]):
            distances.append(
                distances[-1] + RouteGuidanceController._distance_miles(start, end)
            )
        return tuple(distances)

    @staticmethod
    def _distance_miles(first: GeoPoint, second: GeoPoint) -> float:
        lat1 = math.radians(first.latitude)
        lat2 = math.radians(second.latitude)
        delta_lat = lat2 - lat1
        delta_lon = math.radians(second.longitude - first.longitude)
        value = (
            math.sin(delta_lat / 2.0) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2.0) ** 2
        )
        return 2.0 * _EARTH_RADIUS_MILES * math.asin(min(1.0, math.sqrt(value)))
