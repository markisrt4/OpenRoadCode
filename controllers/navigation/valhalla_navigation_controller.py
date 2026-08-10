from __future__ import annotations

from typing import Any

from controllers.navigation.navigation_controller_if import (
    NavigationControllerIf,
)
from controllers.navigation.navigation_types import (
    GeoPoint,
    NavigationManeuver,
    NavigationRoute,
    RouteRequest,
    TravelMode,
)
from protocols.valhalla.valhalla_http_client import (
    ValhallaHttpClient,
)


class ValhallaNavigationController(NavigationControllerIf):
    """Navigation controller backed by a Valhalla routing service."""

    def __init__(
        self,
        client: ValhallaHttpClient,
    ) -> None:
        self._client = client

    def is_available(self) -> bool:
        try:
            self._client.status()
            return True
        except Exception:
            return False

    def calculate_route(
        self,
        request: RouteRequest,
    ) -> NavigationRoute:
        response = self._client.route(
            self._create_route_request(request)
        )

        return self._parse_route(response)

    def _create_route_request(
        self,
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
            "costing": self._costing_name(
                request.travel_mode
            ),
            "units": "miles",
            "language": "en-US",
            "directions_options": {
                "units": "miles",
            },
        }

    def _parse_route(
        self,
        response: dict[str, Any],
    ) -> NavigationRoute:
        trip = response.get("trip")

        if not isinstance(trip, dict):
            raise ValueError(
                "Valhalla response did not contain a trip"
            )

        summary = trip.get("summary")

        if not isinstance(summary, dict):
            raise ValueError(
                "Valhalla trip did not contain a summary"
            )

        legs = trip.get("legs")

        if not isinstance(legs, list) or not legs:
            raise ValueError(
                "Valhalla trip did not contain route legs"
            )

        shape: list[GeoPoint] = []
        maneuvers: list[NavigationManeuver] = []

        for leg in legs:
            if not isinstance(leg, dict):
                continue

            encoded_shape = leg.get("shape")

            if isinstance(encoded_shape, str):
                leg_shape = self._decode_polyline6(
                    encoded_shape
                )

                if shape and leg_shape:
                    leg_shape = leg_shape[1:]

                shape.extend(leg_shape)

            raw_maneuvers = leg.get("maneuvers", [])

            if not isinstance(raw_maneuvers, list):
                continue

            for maneuver in raw_maneuvers:
                parsed = self._parse_maneuver(maneuver)

                if parsed is not None:
                    maneuvers.append(parsed)

        return NavigationRoute(
            distance_miles=float(
                summary.get("length", 0.0)
            ),
            duration_seconds=float(
                summary.get("time", 0.0)
            ),
            shape=tuple(shape),
            maneuvers=tuple(maneuvers),
        )

    @staticmethod
    def _parse_maneuver(
        maneuver: object,
    ) -> NavigationManeuver | None:
        if not isinstance(maneuver, dict):
            return None

        instruction = maneuver.get("instruction")

        if not isinstance(instruction, str):
            return None

        verbal = maneuver.get(
            "verbal_pre_transition_instruction"
        )

        if not isinstance(verbal, str):
            verbal = None

        return NavigationManeuver(
            instruction=instruction,
            verbal_instruction=verbal,
            distance_miles=float(
                maneuver.get("length", 0.0)
            ),
            duration_seconds=float(
                maneuver.get("time", 0.0)
            ),
            begin_shape_index=int(
                maneuver.get("begin_shape_index", 0)
            ),
            end_shape_index=int(
                maneuver.get("end_shape_index", 0)
            ),
        )

    @staticmethod
    def _costing_name(
        travel_mode: TravelMode,
    ) -> str:
        costing = {
            TravelMode.AUTO: "auto",
            TravelMode.BICYCLE: "bicycle",
            TravelMode.PEDESTRIAN: "pedestrian",
            TravelMode.MOTORCYCLE: "motorcycle",
        }

        return costing[travel_mode]

    @staticmethod
    def _decode_polyline6(
        encoded: str,
    ) -> list[GeoPoint]:
        points: list[GeoPoint] = []

        latitude = 0
        longitude = 0
        index = 0

        while index < len(encoded):
            latitude_delta, index = (
                ValhallaNavigationController
                ._decode_polyline_value(
                    encoded,
                    index,
                )
            )

            longitude_delta, index = (
                ValhallaNavigationController
                ._decode_polyline_value(
                    encoded,
                    index,
                )
            )

            latitude += latitude_delta
            longitude += longitude_delta

            points.append(
                GeoPoint(
                    latitude=latitude / 1_000_000.0,
                    longitude=longitude / 1_000_000.0,
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

            result |= (value & 0x1F) << shift
            shift += 5

            if value < 0x20:
                break

        delta = (
            ~(result >> 1)
            if result & 1
            else result >> 1
        )

        return delta, index
