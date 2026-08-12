# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for provider-neutral map and route-guidance contracts."""

from dataclasses import FrozenInstanceError
from datetime import datetime
import unittest

from ui.navigation import (
    GeoPoint,
    LaneDirection,
    LaneGuidance,
    LaneGuidanceUiIf,
    LaneGuidanceUiStub,
    ManeuverType,
    MapMarker,
    MapMarkerKind,
    MapRequestHandlerIf,
    MapRequestHandlerStub,
    MapState,
    MapUiIf,
    MapUiStub,
    MapViewport,
    NavigationStatus,
    RouteGeometry,
    RouteGuidanceState,
    RouteGuidanceUiIf,
    RouteGuidanceUiStub,
    RouteManeuver,
    RouteRequestHandlerIf,
    RouteRequestHandlerStub,
    RouteSummary,
    TravelLane,
    TravelMode,
)


class MapRouteContractTest(unittest.TestCase):
    def test_complete_map_snapshot_is_immutable(self) -> None:
        current = GeoPoint(0.74, -1.45, 180.0)
        state = MapState(
            viewport=MapViewport(current, 15.0, bearing_rad=1.2),
            markers=(MapMarker("vehicle", current, MapMarkerKind.CURRENT_POSITION),),
            route_geometry=RouteGeometry((current, GeoPoint(0.75, -1.44))),
            style_id="day",
        )

        with self.assertRaises(FrozenInstanceError):
            state.loading = True  # type: ignore[misc]

    def test_route_and_lane_values_cover_turn_by_turn_presentation(self) -> None:
        maneuver = RouteManeuver(
            ManeuverType.TURN_RIGHT,
            "Turn right onto Main Street",
            250.0,
            street_name="Main Street",
        )
        state = RouteGuidanceState(
            status=NavigationStatus.ACTIVE,
            destination=GeoPoint(0.75, -1.44),
            travel_mode=TravelMode.AUTO,
            summary=RouteSummary(12_500.0, 900.0, datetime(2030, 1, 1, 12, 0)),
            current_road="Oak Street",
            next_maneuver=maneuver,
        )
        lanes = LaneGuidance((
            TravelLane((LaneDirection.STRAIGHT,)),
            TravelLane((LaneDirection.RIGHT,), True, LaneDirection.RIGHT),
        ))

        self.assertEqual(state.next_maneuver, maneuver)
        self.assertTrue(lanes.lanes[1].recommended)

    def test_interfaces_are_narrow_and_stubs_are_concrete(self) -> None:
        self.assertEqual(
            MapUiIf.__abstractmethods__,
            {"set_map_state", "set_map_request_handler"},
        )
        self.assertEqual(
            RouteGuidanceUiIf.__abstractmethods__,
            {"set_route_guidance", "set_route_request_handler"},
        )
        self.assertEqual(
            LaneGuidanceUiIf.__abstractmethods__,
            {"set_lane_guidance"},
        )
        self.assertIsInstance(MapUiStub(), MapUiIf)
        self.assertIsInstance(RouteGuidanceUiStub(), RouteGuidanceUiIf)
        self.assertIsInstance(LaneGuidanceUiStub(), LaneGuidanceUiIf)

    def test_request_contracts_cover_map_and_route_intent(self) -> None:
        self.assertEqual(
            MapRequestHandlerIf.__abstractmethods__,
            {
                "request_recenter",
                "request_center_on",
                "request_zoom",
                "request_bearing",
                "request_pitch",
                "request_style",
            },
        )
        self.assertEqual(
            RouteRequestHandlerIf.__abstractmethods__,
            {
                "request_start_route",
                "request_cancel_route",
                "request_add_waypoint",
                "request_remove_waypoint",
                "request_select_alternative",
                "request_recalculate_route",
                "request_travel_mode",
                "request_voice_guidance_muted",
            },
        )
        self.assertIsInstance(MapRequestHandlerStub(), MapRequestHandlerIf)
        self.assertIsInstance(RouteRequestHandlerStub(), RouteRequestHandlerIf)


if __name__ == "__main__":
    unittest.main()
