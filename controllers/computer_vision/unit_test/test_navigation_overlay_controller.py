# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Frame matching, degraded telemetry and lifecycle behavior of the video HUD."""

from unittest.mock import Mock

import pytest

from controllers.computer_vision.navigation_overlay_controller import NavigationOverlayController
from ui.navigation.route_types import RouteTurn
from ui.vision.navigation_overlay import (
    OverlayGuidance, OverlayMotion, OverlayPosition, OverlayGpsStatus,
)


def setup_overlay():
    dispatcher, ui = Mock(), Mock()
    dispatcher.schedule_ui_callback.side_effect = lambda delay, callback: callback
    now = [10.0]
    controller = NavigationOverlayController(dispatcher, ui, clock=lambda: now[0])
    controller.request_activate()
    return controller, dispatcher, ui, now


def seed(controller, timestamp=9.5):
    controller.update_position(OverlayPosition(timestamp, True, accuracy_m=5))
    controller.update_motion(OverlayMotion(timestamp, 10))
    controller.update_guidance(OverlayGuidance(
        timestamp, "Turn left onto Main Street", RouteTurn.LEFT, "Main Street", 100,
    ))


def test_frame_never_uses_navigation_received_after_capture():
    controller, _, _, _ = setup_overlay()
    seed(controller, 9.5)
    controller.update_guidance(OverlayGuidance(9.9, "Turn right", RouteTurn.RIGHT))
    controller.set_frame(9.8)
    state = controller.snapshot()
    assert state.turn == RouteTurn.LEFT
    assert state.guidance_timestamp_s <= state.frame_timestamp_s
    controller.set_frame(10)
    assert controller.snapshot().turn == RouteTurn.RIGHT


def test_old_video_hides_actionable_route_and_speed():
    controller, _, _, now = setup_overlay()
    seed(controller)
    controller.set_frame(9.8)
    assert controller.snapshot().speed_m_s == 10
    now[0] = 12
    state = controller.snapshot()
    assert state.video_stale
    assert state.instruction is None and state.speed_m_s is None


def test_fresh_frames_do_not_make_old_navigation_fresh():
    controller, _, _, now = setup_overlay()
    seed(controller)
    now[0] = 16
    controller.set_frame(16)
    state = controller.snapshot()
    assert state.gps_status == OverlayGpsStatus.STALE
    assert state.guidance_stale
    assert state.distance_m is None and state.speed_m_s is None


@pytest.mark.parametrize("cached,accuracy,status", [
    (False, 3, OverlayGpsStatus.LIVE), (False, 40, OverlayGpsStatus.WEAK),
    (True, 3, OverlayGpsStatus.CACHED),
])
def test_live_weak_and_cached_gps_are_distinct(cached, accuracy, status):
    controller, _, _, _ = setup_overlay()
    controller.update_position(OverlayPosition(9.8, True, cached, accuracy))
    controller.update_motion(OverlayMotion(9.8, 10, cached))
    controller.set_frame(10)
    assert controller.snapshot().gps_status == status
    if cached:
        assert controller.snapshot().speed_m_s is None


def test_end_route_clears_old_maneuver_without_waiting_for_expiry():
    controller, _, _, _ = setup_overlay()
    seed(controller)
    controller.update_guidance(OverlayGuidance(9.9))
    controller.set_frame(10)
    assert controller.snapshot().instruction is None
    assert controller.snapshot().turn == RouteTurn.UNKNOWN


def test_delayed_samples_do_not_overwrite_newer_state():
    controller, _, _, _ = setup_overlay()
    seed(controller)
    controller.update_motion(OverlayMotion(9.0, 50))
    controller.update_guidance(OverlayGuidance(9.0, "Wrong turn", RouteTurn.RIGHT))
    controller.set_frame(10)
    assert controller.snapshot().speed_m_s == 10
    assert controller.snapshot().turn == RouteTurn.LEFT


def test_hide_and_close_drop_old_timers_even_after_reactivation():
    controller, dispatcher, ui, _ = setup_overlay()
    old_tick = dispatcher.schedule_ui_callback.call_args.args[1]
    controller.request_deactivate()
    dispatcher.cancel_ui_callback.assert_called_once()
    controller.request_activate()
    ui.reset_mock()
    old_tick()
    ui.set_navigation_overlay.assert_not_called()
    live_tick = dispatcher.schedule_ui_callback.call_args.args[1]
    controller.close()
    ui.reset_mock()
    live_tick()
    seed(controller)
    controller.set_frame(10)
    ui.set_navigation_overlay.assert_not_called()


def test_visibility_toggle_keeps_telemetry_and_survives_screen_reentry():
    controller, _, _, _ = setup_overlay()
    seed(controller)
    controller.request_enabled(False)
    controller.request_deactivate()
    controller.request_activate()
    controller.set_frame(10)
    assert not controller.snapshot().enabled
    controller.request_enabled(True)
    assert controller.snapshot().instruction == "Turn left onto Main Street"


def test_health_timer_expires_frozen_video_without_new_camera_frames():
    controller, dispatcher, ui, now = setup_overlay()
    seed(controller)
    controller.set_frame(10)
    now[0] = 12
    dispatcher.schedule_ui_callback.call_args.args[1]()
    assert ui.set_navigation_overlay.call_args.args[0].video_stale


def test_off_route_and_arrival_are_explicit_states():
    controller, _, _, _ = setup_overlay()
    seed(controller)
    controller.update_guidance(OverlayGuidance(9.9, off_route=True))
    controller.set_frame(10)
    assert controller.snapshot().off_route
    controller.update_guidance(OverlayGuidance(10, complete=True))
    controller.set_frame(10)
    assert controller.snapshot().complete
    assert not controller.snapshot().off_route
