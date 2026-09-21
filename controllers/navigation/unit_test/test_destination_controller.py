# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from controllers.navigation.destination_controller import DestinationController
from controllers.navigation.geocoding import GeocodedLocation
from controllers.route_planning.route_planning_types import (
    GeoPoint,
    RouteResult,
    TravelMode,
)


class _Geocoder:
    def __init__(self, result: GeocodedLocation | None) -> None:
        self.result = result
        self.queries: list[str] = []

    def geocode(self, address: str) -> GeocodedLocation | None:
        self.queries.append(address)
        return self.result


class _RoutePlanner:
    is_available = True
    status_message = None

    def __init__(self) -> None:
        self.requests = []
        self.result = RouteResult(
            distance_miles=1.0,
            duration_seconds=60.0,
            shape=(),
            maneuvers=(),
        )

    def calculate_route(self, request):
        self.requests.append(request)
        return self.result


def test_route_to_geocodes_destination_and_plans_route() -> None:
    geocoder = _Geocoder(
        GeocodedLocation(
            formatted_address="100 Example Avenue, Testville, MI",
            latitude_deg=42.5,
            longitude_deg=-83.1,
        )
    )
    planner = _RoutePlanner()
    controller = DestinationController(geocoder, planner)
    origin = GeoPoint(latitude=42.0, longitude=-83.0)

    result = controller.route_to(
        origin,
        "100 Example Avenue, Testville, MI",
        TravelMode.AUTO,
    )

    assert result is not None
    assert result.destination.formatted_address == "100 Example Avenue, Testville, MI"
    assert result.route is planner.result
    assert geocoder.queries == ["100 Example Avenue, Testville, MI"]
    assert planner.requests[0].origin == origin
    assert planner.requests[0].destination == GeoPoint(
        latitude=42.5,
        longitude=-83.1,
    )
    assert planner.requests[0].travel_mode is TravelMode.AUTO


def test_route_to_returns_none_when_destination_cannot_be_resolved() -> None:
    planner = _RoutePlanner()
    controller = DestinationController(_Geocoder(None), planner)

    result = controller.route_to(
        GeoPoint(latitude=42.0, longitude=-83.0),
        "Missing Place",
    )

    assert result is None
    assert planner.requests == []
