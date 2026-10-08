# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Radar loading, pending requests and shared visibility through a headless UI contract."""

from unittest.mock import Mock, patch
from controllers.weather.radar_replay_controller import RadarReplayController
from ui.weather.radar_ui_stub import RadarUiStub
from ui.weather.radar_ui_if import RadarPalette


def component(enabled=False):
    backend = Mock(enabled=enabled, frame_time=None, frame_times=(), frame_index=None,
                   palette=RadarPalette.UNIVERSAL, is_forecast=False)
    return RadarReplayController(Mock(), RadarUiStub(), backend)


def test_pending_radar_can_be_disabled_before_frame_finishes_loading():
    screen = component()
    with patch("controllers.weather.radar_replay_controller.threading.Thread") as thread:
        screen.request_enabled(True)
        assert screen._ui.state.enabled
        load = thread.call_args.kwargs["target"]
        screen.request_enabled(False)
        assert not screen._ui.state.enabled
        load()
    completed = screen._host.schedule_ui_callback.call_args.args[1]
    completed()
    screen._radar_controller.show_frames.assert_not_called()
    screen._radar_controller.hide.assert_called_once_with()


def test_failed_download_resets_both_screens_and_reports_error():
    screen = component(True)
    screen._on_radar_visibility_changed = Mock()
    screen._radar_load_failed("provider timed out")
    assert screen._ui.state.enabled is False
    screen._radar_controller.hide.assert_called_once_with()
    screen._on_radar_visibility_changed.assert_called_once_with()
    assert screen._ui.state.status == "Radar unavailable: provider timed out"


def test_download_presents_on_ui_thread_and_retries_slow_renderer():
    screen = component()
    screen._refresh_radar = Mock()
    with patch("controllers.weather.radar_replay_controller.threading.Thread") as thread:
        screen.request_enabled(True)
        thread.call_args.kwargs["target"]()
    screen._radar_controller.show_frames.assert_not_called()
    screen._host.schedule_ui_callback.call_args.args[1]()
    screen._radar_controller.show_frames.assert_called_once_with(
        screen._radar_controller.load_frames.return_value)
    replays = screen._host.schedule_ui_callback.call_args_list[1:]
    assert [call.args[0] for call in replays] == [300, 1200, 2500, 5000]
    replays[-1].args[1]()
    screen._refresh_radar.assert_called_once_with()

