# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from controllers.route_guidance import RouteGuidanceController
from controllers.route_planning.route_planning_types import (
    GeoPoint,
    RouteManeuver,
    RouteResult,
)


def _route() -> RouteResult:
    shape = (
        GeoPoint(42.0000, -83.0000),
        GeoPoint(42.0000, -82.9900),
        GeoPoint(42.0100, -82.9900),
        GeoPoint(42.0100, -82.9800),
    )
    maneuvers = (
        RouteManeuver("Head east", None, 0.5, 60.0, 0, 1),
        RouteManeuver("Turn left", None, 0.7, 90.0, 1, 2),
        RouteManeuver("Turn right", None, 0.5, 60.0, 2, 3),
    )
    return RouteResult(1.7, 210.0, shape, maneuvers)


def test_progress_selects_maneuver_and_decreases_distance() -> None:
    controller = RouteGuidanceController(_route())
    start = controller.update(GeoPoint(42.0000, -82.9995))
    later = controller.update(GeoPoint(42.0000, -82.9910))
    assert start.current_maneuver_index == 0
    assert later.current_maneuver_index == 0
    assert later.distance_along_route_miles > start.distance_along_route_miles
    assert later.distance_remaining_miles < start.distance_remaining_miles
    assert later.distance_to_maneuver_miles < start.distance_to_maneuver_miles
    assert not later.off_route


def test_progress_advances_to_next_maneuver() -> None:
    controller = RouteGuidanceController(_route())
    state = controller.update(GeoPoint(42.0050, -82.9900))
    assert state.current_maneuver_index == 1
    assert state.current_maneuver is not None
    assert state.current_maneuver.instruction == "Turn left"


def test_maneuver_advances_at_exact_shape_boundary() -> None:
    controller = RouteGuidanceController(_route())
    state = controller.update(GeoPoint(42.0000, -82.9900))
    assert state.current_maneuver_index == 1
    assert state.current_maneuver is not None
    assert state.current_maneuver.instruction == "Turn left"


def test_final_maneuver_remains_active_at_destination() -> None:
    controller = RouteGuidanceController(_route())
    state = controller.update(GeoPoint(42.0100, -82.9800))
    assert state.current_maneuver_index == 2
    assert state.current_maneuver is not None
    assert state.current_maneuver.instruction == "Turn right"
    assert state.distance_to_maneuver_miles == 0.0
    assert state.route_complete


def test_progress_does_not_move_backward_with_noisy_fix() -> None:
    controller = RouteGuidanceController(_route())
    forward = controller.update(GeoPoint(42.0060, -82.9900))
    noisy_backward = controller.update(GeoPoint(42.0040, -82.9900))
    assert noisy_backward.distance_along_route_miles == forward.distance_along_route_miles


def test_off_route_is_detected() -> None:
    controller = RouteGuidanceController(_route(), off_route_threshold_miles=0.05)
    state = controller.update(GeoPoint(42.0050, -82.9850))
    assert state.off_route
    assert state.distance_from_route_miles > 0.05


def test_off_route_recovers_only_inside_on_route_threshold() -> None:
    controller = RouteGuidanceController(
        _route(), off_route_threshold_miles=0.05, on_route_threshold_miles=0.03
    )
    off_route = controller.update(GeoPoint(42.0050, -82.9850))
    still_off_route = controller.update(GeoPoint(42.0050, -82.9893))
    recovered = controller.update(GeoPoint(42.0050, -82.9898))
    assert off_route.off_route
    assert 0.03 < still_off_route.distance_from_route_miles < 0.05
    assert still_off_route.off_route
    assert recovered.distance_from_route_miles < 0.03
    assert not recovered.off_route


def test_off_route_hysteresis_prevents_threshold_flapping() -> None:
    controller = RouteGuidanceController(
        _route(), off_route_threshold_miles=0.05, on_route_threshold_miles=0.03
    )
    controller.update(GeoPoint(42.0050, -82.9850))
    near_outer_threshold = controller.update(GeoPoint(42.0050, -82.9893))
    assert 0.03 < near_outer_threshold.distance_from_route_miles < 0.05
    assert near_outer_threshold.off_route


def test_on_route_threshold_cannot_exceed_off_route_threshold() -> None:
    try:
        RouteGuidanceController(
            _route(), off_route_threshold_miles=0.05, on_route_threshold_miles=0.06
        )
    except ValueError as error:
        assert "must not exceed" in str(error)
    else:
        raise AssertionError("Expected ValueError")


def test_arrival_is_detected_near_destination() -> None:
    controller = RouteGuidanceController(_route(), arrival_threshold_miles=0.03)
    state = controller.update(GeoPoint(42.0100, -82.9801))
    assert state.route_complete
    assert not state.off_route


def test_requires_route_shape() -> None:
    route = RouteResult(0.0, 0.0, (GeoPoint(42.0, -83.0),), ())
    try:
        RouteGuidanceController(route)
    except ValueError as error:
        assert "at least two points" in str(error)
    else:
        raise AssertionError("Expected ValueError")


def test_replace_route_resets_progress_and_off_route_state() -> None:
    controller = RouteGuidanceController(
        _route(), off_route_threshold_miles=0.05, on_route_threshold_miles=0.03
    )
    before = controller.update(GeoPoint(42.0050, -82.9850))
    assert before.off_route
    assert before.distance_along_route_miles > 0.0

    replacement = RouteResult(
        0.5,
        60.0,
        (
            GeoPoint(42.0050, -82.9850),
            GeoPoint(42.0050, -82.9750),
        ),
        (RouteManeuver("Continue east", None, 0.5, 60.0, 0, 1),),
    )
    controller.replace_route(replacement)
    after = controller.update(GeoPoint(42.0050, -82.9850))

    assert not after.off_route
    assert after.distance_along_route_miles == 0.0
    assert after.current_maneuver is not None
    assert after.current_maneuver.instruction == "Continue east"
