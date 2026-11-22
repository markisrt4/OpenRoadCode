import math
from unittest.mock import Mock

from controllers.navigation.route_overlay_controller import RouteOverlayController
from controllers.route_planning.route_planning_types import GeoPoint, RouteManeuver, RouteResult
from messaging.contracts.route_guidance import RouteGuidanceStateData, RouteGuidanceStateMessage


def route(point_count=3):
    return RouteResult(1, 60,
        tuple(GeoPoint(42 + index / 100, -83) for index in range(point_count)),
        (RouteManeuver('Turn left', None, 1, 30, 0, min(1, point_count - 1)),))


def test_route_result_becomes_bounded_si_overlay_and_cancel_clears_it():
    update = Mock()
    controller = RouteOverlayController(update, point_limit=4)
    controller.update_route(route(10))
    state = update.call_args.args[0]
    assert len(state.geometry.points) <= 4
    assert state.geometry.points[-1] == state.destination
    assert math.isclose(state.destination.latitude_rad, math.radians(42.09))
    controller.update_route(None)
    assert not update.call_args.args[0].geometry.points


def test_guidance_marks_current_maneuver_and_off_route_status():
    update = Mock()
    controller = RouteOverlayController(update)
    controller.update_route(route())
    controller.update_guidance(RouteGuidanceStateMessage(1, 'navigation',
        RouteGuidanceStateData(0, 100, 12, 0, 'Turn left', None, 40, True, False)))
    state = update.call_args.args[0]
    assert state.maneuver == state.geometry.points[1]
    assert state.instruction == 'Turn left'
    assert state.off_route
