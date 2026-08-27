# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Valhalla implementation of the route-planning controller."""

from __future__ import annotations

import logging
from typing import Any

from controllers.route_planning.route_planning_controller_if import (
    RoutePlanningControllerIf,
)
from controllers.route_planning.route_planning_types import (
    GeoPoint,
    RouteManeuver,
    RouteRequest,
    RouteResult,
    TravelMode,
)
from protocols.valhalla.valhalla_http_client import (
    ValhallaHttpClient,
)


LOGGER = logging.getLogger(__name__)


class ValhallaRoutePlanningController(
    RoutePlanningControllerIf
):
    """Calculate routes using a Valhalla service."""

    def __init__(
        self,
        client: ValhallaHttpClient,
    ) -> None:
        self._client = client

        self._is_available = False
        self._status_message: str | None = (
            "Valhalla availability has not been checked"
        )

        self._refresh_status()

    @property
    def is_available(self) -> bool:
        return self._is_available

    @property
    def status_message(self) -> str | None:
        return self._status_message

    def calculate_route(
        self,
        request: RouteRequest,
    ) -> RouteResult:
        """Calculate a route using Valhalla."""

        try:
            response = self._client.route(
                self._create_route_request(request)
            )

            route = self._parse_route(response)

            self._is_available = True
            self._status_message = None

            return route

        except Exception as exc:
            self._is_available = False
            self._status_message = (
                f"Valhalla route calculation failed: {exc}"
            )

            raise

    def _refresh_status(self) -> None:
        try:
            self._client.status()

            self._is_available = True
            self._status_message = None

        except Exception as exc:
            self._is_available = False
            self._status_message = (
                f"Valhalla unavailable: {exc}"
            )

            LOGGER.debug(
                "Valhalla availability check failed",
                exc_info=True,
            )

    @staticmethod
    def _create_route_request(
        request: RouteRequest,
    ) -> dict[str, Any]:
        return {
            "locations": [
                {
                    "lat": request.origin.latitude,
                    "lon": request.origin.longitude,
                    "type": "break",
                },
                {
                    "lat": request.destination.latitude,
                    "lon": request.destination.longitude,
                    "type": "break",
                },
            ],
            "costing": (
                ValhallaRoutePlanningController
                ._costing_name(request.travel_mode)
            ),
            "units": "miles",
            "language": "en-US",
        }

    @staticmethod
    def _costing_name(
        travel_mode: TravelMode,
    ) -> str:
        costing_names = {
            TravelMode.AUTO: "auto",
            TravelMode.BICYCLE: "bicycle",
            TravelMode.PEDESTRIAN: "pedestrian",
            TravelMode.MOTORCYCLE: "motorcycle",
        }

        return costing_names[travel_mode]

    @classmethod
    def _parse_route(
        cls,
        response: dict[str, Any],
    ) -> RouteResult:
        trip = response.get("trip")

        if not isinstance(trip, dict):
            raise ValueError(
                "Valhalla response does not contain a trip"
            )

        summary = trip.get("summary")

        if not isinstance(summary, dict):
            raise ValueError(
                "Valhalla trip does not contain a summary"
            )

        legs = trip.get("legs")

        if not isinstance(legs, list) or not legs:
            raise ValueError(
                "Valhalla trip does not contain route legs"
            )

        route_shape: list[GeoPoint] = []
        route_maneuvers: list[RouteManeuver] = []

        for leg in legs:
            if not isinstance(leg, dict):
                continue

            cls._append_leg_shape(
                route_shape,
                leg,
            )

            cls._append_leg_maneuvers(
                route_maneuvers,
                leg,
            )

        return RouteResult(
            distance_miles=float(
                summary.get("length", 0.0)
            ),
            duration_seconds=float(
                summary.get("time", 0.0)
            ),
            shape=tuple(route_shape),
            maneuvers=tuple(route_maneuvers),
        )

    @classmethod
    def _append_leg_shape(
        cls,
        route_shape: list[GeoPoint],
        leg: dict[str, Any],
    ) -> None:
        encoded_shape = leg.get("shape")

        if not isinstance(encoded_shape, str):
            return

        leg_shape = cls._decode_polyline6(
            encoded_shape
        )

        # Adjacent Valhalla legs normally share their
        # endpoint/start point. Avoid duplicating it.
        if route_shape and leg_shape:
            leg_shape = leg_shape[1:]

        route_shape.extend(leg_shape)

    @classmethod
    def _append_leg_maneuvers(
        cls,
        route_maneuvers: list[RouteManeuver],
        leg: dict[str, Any],
    ) -> None:
        maneuvers = leg.get("maneuvers")

        if not isinstance(maneuvers, list):
            return

        for maneuver in maneuvers:
            parsed = cls._parse_maneuver(maneuver)

            if parsed is not None:
                route_maneuvers.append(parsed)

    @staticmethod
    def _parse_maneuver(
        maneuver: object,
    ) -> RouteManeuver | None:
        if not isinstance(maneuver, dict):
            return None

        instruction = maneuver.get("instruction")

        if not isinstance(instruction, str):
            return None

        verbal_instruction = maneuver.get(
            "verbal_pre_transition_instruction"
        )

        if not isinstance(
            verbal_instruction,
            str,
        ):
            verbal_instruction = None

        return RouteManeuver(
            instruction=instruction,
            verbal_instruction=verbal_instruction,
            distance_miles=float(
                maneuver.get("length", 0.0)
            ),
            duration_seconds=float(
                maneuver.get("time", 0.0)
            ),
            begin_shape_index=int(
                maneuver.get(
                    "begin_shape_index",
                    0,
                )
            ),
            end_shape_index=int(
                maneuver.get(
                    "end_shape_index",
                    0,
                )
            ),
        )

    @classmethod
    def _decode_polyline6(
        cls,
        encoded: str,
    ) -> list[GeoPoint]:
        """Decode a Valhalla six-digit encoded polyline."""

        points: list[GeoPoint] = []

        latitude = 0
        longitude = 0
        index = 0

        while index < len(encoded):
            latitude_delta, index = (
                cls._decode_polyline_value(
                    encoded,
                    index,
                )
            )

            longitude_delta, index = (
                cls._decode_polyline_value(
                    encoded,
                    index,
                )
            )

            latitude += latitude_delta
            longitude += longitude_delta

            points.append(
                GeoPoint(
                    latitude=(
                        latitude / 1_000_000.0
                    ),
                    longitude=(
                        longitude / 1_000_000.0
                    ),
                )
            )

        return points

    @staticmethod
    def _decode_polyline_value(
        encoded: str,
        index: int,
    ) -> tuple[int, int]:
        result = 0
        shift = 0

        while True:
            if index >= len(encoded):
                raise ValueError(
                    "Invalid Valhalla encoded polyline"
                )

            value = ord(encoded[index]) - 63
            index += 1

            result |= (
                value & 0x1F
            ) << shift

            shift += 5

            if value < 0x20:
                break

        if result & 1:
            delta = ~(result >> 1)
        else:
            delta = result >> 1

        return delta, index

