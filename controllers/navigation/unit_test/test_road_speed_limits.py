# SPDX-License-Identifier: MIT
"""GPS freshness and asynchronous speed-limit retirement."""

from unittest.mock import Mock
import pytest

from controllers.navigation.road_speed_limit_controller import RoadSpeedLimitController
from ui.navigation.map_ui_if import GeoPoint
from ui.navigation.road_speed_limit_ui_if import RoadSpeedLimitState


def setup():
    now, work, deliveries = [0.0], [], []
    provider, ui, dispatcher = Mock(), Mock(), Mock()
    dispatcher.dispatch_ui.side_effect = deliveries.append
    provider.lookup.return_value = RoadSpeedLimitState(20)
    controller = RoadSpeedLimitController(provider, ui, dispatcher, work.append, lambda: now[0])
    return controller, provider, ui, dispatcher, now, work, deliveries


def trace(controller):
    controller.update_position(GeoPoint(0.7, -1.4), 5)
    controller.update_position(GeoPoint(0.700002, -1.4), 5)


def test_lookup_is_deferred_and_only_one_is_in_flight():
    controller, provider, ui, _, _, work, deliveries = setup()
    trace(controller)
    controller.update_position(GeoPoint(0.700003, -1.4), 5)
    assert len(work) == 1
    provider.lookup.assert_not_called()
    work.pop()()
    ui.set_road_speed_limit.assert_called_with(RoadSpeedLimitState())
    deliveries.pop()()
    ui.set_road_speed_limit.assert_called_with(RoadSpeedLimitState(20))


@pytest.mark.parametrize("retire", ["close", "weak_gps", "teleport"])
def test_old_completion_cannot_restore_limit(retire):
    controller, _, ui, _, _, work, deliveries = setup()
    trace(controller)
    work.pop()()
    if retire == "close":
        controller.close()
    elif retire == "weak_gps":
        controller.update_position(GeoPoint(0.7, -1.4), 100)
    else:
        controller.update_position(GeoPoint(0.8, -1.4), 5)
    ui.reset_mock()
    deliveries.pop()()
    assert RoadSpeedLimitState(20) not in [call.args[0] for call in ui.set_road_speed_limit.call_args_list]


def test_missing_fixes_expire_sign_and_shutdown_cancels_timer():
    controller, _, ui, dispatcher, now, work, deliveries = setup()
    controller.start()
    trace(controller)
    work.pop()()
    deliveries.pop()()
    now[0] = 10
    dispatcher.schedule_ui_callback.call_args.args[1]()
    ui.set_road_speed_limit.assert_called_with(RoadSpeedLimitState())
    controller.close()
    dispatcher.cancel_ui_callback.assert_called_once()


def test_closed_queue_does_not_call_provider_and_failures_clear_sign():
    controller, provider, ui, _, _, work, deliveries = setup()
    trace(controller)
    controller.close()
    work.pop()()
    provider.lookup.assert_not_called()
    assert not deliveries
    controller, provider, ui, _, _, work, deliveries = setup()
    provider.lookup.side_effect = RuntimeError("no tiles")
    trace(controller)
    work.pop()()
    deliveries.pop()()
    ui.set_road_speed_limit.assert_called_with(RoadSpeedLimitState())
