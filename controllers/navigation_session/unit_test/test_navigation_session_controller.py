# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from controllers.navigation_session import NavigationSessionController
from controllers.route_guidance import ReroutePolicy, RouteGuidanceController
from controllers.route_guidance.route_guidance_types import RouteGuidanceState
from controllers.route_planning.route_planning_types import (
    GeoPoint,
    RouteManeuver,
    RouteRequest,
    RouteResult,
    TravelMode,
)


def _route(offset: float = 0.0) -> RouteResult:
    return RouteResult(
        1.0,
        120.0,
        (
            GeoPoint(42.0 + offset, -83.0),
            GeoPoint(42.0 + offset, -82.99),
        ),
        (RouteManeuver("Continue", None, 1.0, 120.0, 0, 1),),
    )


def _guidance(*, off_route: bool, complete: bool = False) -> RouteGuidanceState:
    return RouteGuidanceState(
        distance_along_route_miles=0.2,
        distance_remaining_miles=0.8,
        distance_from_route_miles=0.1 if off_route else 0.0,
        current_maneuver_index=0,
        current_maneuver=None,
        distance_to_maneuver_miles=0.8,
        off_route=off_route,
        route_complete=complete,
    )


def test_start_owns_destination_mode_and_route() -> None:
    initial = _route()
    guidance = RouteGuidanceController(initial)
    session = NavigationSessionController(
        lambda request: initial,
        guidance,
        ReroutePolicy(off_route_delay_s=0.0),
    )
    request = RouteRequest(
        GeoPoint(42.0, -83.0),
        GeoPoint(42.1, -82.9),
        TravelMode.AUTO,
    )

    session.start(request, route=initial)

    assert session.state is not None
    assert session.state.destination == request.destination
    assert session.state.travel_mode is TravelMode.AUTO
    assert session.state.route is initial


def test_sustained_off_route_calculates_from_current_position() -> None:
    clock = [0.0]
    initial = _route()
    replacement = _route(0.01)
    requests = []

    def calculate(request: RouteRequest) -> RouteResult:
        requests.append(request)
        return replacement

    guidance = RouteGuidanceController(initial)
    session = NavigationSessionController(
        calculate,
        guidance,
        ReroutePolicy(off_route_delay_s=3.0, clock=lambda: clock[0]),
    )
    destination = GeoPoint(42.1, -82.9)
    session.start(
        RouteRequest(GeoPoint(42.0, -83.0), destination, TravelMode.AUTO),
        route=initial,
    )
    current = GeoPoint(42.02, -82.98)

    assert session.update(current, _guidance(off_route=True)) is None
    clock[0] = 3.1
    result = session.update(current, _guidance(off_route=True))

    assert result is replacement
    assert requests == [RouteRequest(current, destination, TravelMode.AUTO)]
    assert session.state is not None
    assert session.state.route is replacement


def test_route_changed_callback_receives_replacement() -> None:
    initial = _route()
    replacement = _route(0.01)
    changed = []
    guidance = RouteGuidanceController(initial)
    session = NavigationSessionController(
        lambda request: replacement,
        guidance,
        ReroutePolicy(off_route_delay_s=0.0),
        on_route_changed=changed.append,
    )
    session.start(
        RouteRequest(GeoPoint(42.0, -83.0), GeoPoint(42.1, -82.9)),
        route=initial,
    )
    changed.clear()

    session.update(GeoPoint(42.02, -82.98), _guidance(off_route=True))

    assert changed == [replacement]


def test_cancel_prevents_reroute() -> None:
    initial = _route()
    calls = []
    guidance = RouteGuidanceController(initial)
    session = NavigationSessionController(
        lambda request: calls.append(request) or _route(0.01),
        guidance,
        ReroutePolicy(off_route_delay_s=0.0),
    )
    session.start(
        RouteRequest(GeoPoint(42.0, -83.0), GeoPoint(42.1, -82.9)),
        route=initial,
    )
    session.cancel()

    assert session.update(GeoPoint(42.02, -82.98), _guidance(off_route=True)) is None
    assert calls == []
