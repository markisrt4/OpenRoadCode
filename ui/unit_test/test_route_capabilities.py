# SPDX-License-Identifier: MIT
"""Optional route operations do not burden baseline implementations."""

import pytest

from ui.navigation import (
    GeoPoint,
    RouteAlternativeRequestHandlerIf,
    RouteRecalculationRequestHandlerIf,
    RouteRequestHandlerIf,
    RouteRequestHandlerStub,
    RouteSimulationRequestHandlerIf,
    RouteTravelModeRequestHandlerIf,
    RouteVoiceGuidanceRequestHandlerIf,
    RouteWaypointRequestHandlerIf,
)
from ui.navigation.route_types import TravelMode


OPTIONAL_CAPABILITIES = (
    RouteAlternativeRequestHandlerIf, RouteRecalculationRequestHandlerIf,
    RouteTravelModeRequestHandlerIf, RouteVoiceGuidanceRequestHandlerIf,
    RouteWaypointRequestHandlerIf, RouteSimulationRequestHandlerIf,
)


def test_baseline_stub_does_not_advertise_advanced_capabilities():
    handler = RouteRequestHandlerStub()
    assert isinstance(handler, RouteRequestHandlerIf)
    handler.request_start_route(GeoPoint(0, 0), TravelMode.AUTO)
    handler.request_cancel_route()
    for capability in OPTIONAL_CAPABILITIES:
        assert not isinstance(handler, capability)


@pytest.mark.parametrize("capability", OPTIONAL_CAPABILITIES)
def test_unimplemented_capabilities_cannot_be_instantiated(capability):
    with pytest.raises(TypeError, match="abstract"):
        capability()


def test_waypoint_capability_can_extend_baseline_without_other_features():
    class WaypointHandler(RouteRequestHandlerStub, RouteWaypointRequestHandlerIf):
        def __init__(self):
            self.waypoints = []
            self.destination = None
            self.travel_mode = None

        def request_start_route_with_waypoints(self, destination, waypoints, travel_mode):
            self.destination = destination
            self.waypoints = list(waypoints)
            self.travel_mode = travel_mode

        def request_add_waypoint(self, waypoint):
            self.waypoints.append(waypoint)

        def request_remove_waypoint(self, waypoint_index):
            self.waypoints.pop(waypoint_index)

    handler = WaypointHandler()
    destination, first, second = GeoPoint(0, 0), GeoPoint(0.1, 0.2), GeoPoint(0.2, 0.3)
    assert isinstance(handler, RouteRequestHandlerIf)
    assert isinstance(handler, RouteWaypointRequestHandlerIf)
    assert not isinstance(handler, RouteVoiceGuidanceRequestHandlerIf)
    handler.request_start_route_with_waypoints(destination, (first,), TravelMode.AUTO)
    handler.request_add_waypoint(second)
    handler.request_remove_waypoint(0)
    assert handler.destination == destination
    assert handler.waypoints == [second]
    assert handler.travel_mode == TravelMode.AUTO
