# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Radar loading, pending requests and shared visibility through a headless UI contract."""

from unittest.mock import Mock, patch

from controllers.weather.radar_replay_controller import RadarReplayController
from ui.weather.radar_ui_if import RadarPalette
from ui.weather.radar_ui_stub import RadarUiStub


def component(enabled: bool = False) -> tuple[RadarReplayController, Mock, Mock, RadarUiStub]:
    backend = Mock(
        enabled=enabled,
        frame_time=None,
        frame_times=(),
        frame_index=None,
        palette=RadarPalette.UNIVERSAL,
        is_forecast=False,
    )
    host, ui = Mock(), RadarUiStub()
    return RadarReplayController(host, ui, backend), host, backend, ui


def test_pending_radar_can_be_disabled_before_frame_finishes_loading() -> None:
    screen, host, backend, ui = component()
    with patch("controllers.weather.radar_replay_controller.threading.Thread") as thread:
        screen.request_enabled(True)
        assert ui.state.enabled
        load = thread.call_args.kwargs["target"]
        screen.request_enabled(False)
        assert not ui.state.enabled
        load()
    completed = host.dispatch_ui.call_args.args[0]
    completed()
    backend.show_frames.assert_not_called()
    backend.hide.assert_called_once_with()


def test_failed_download_resets_both_screens_and_reports_error() -> None:
    screen, _, backend, ui = component(True)
    visibility_changed = Mock()
    screen._on_radar_visibility_changed = visibility_changed
    screen._radar_load_failed("provider timed out")
    assert ui.state.enabled is False
    backend.hide.assert_called_once_with()
    visibility_changed.assert_called_once_with()
    assert ui.state.status == "Radar unavailable: provider timed out"


def test_download_presents_on_ui_thread_and_retries_slow_renderer() -> None:
    screen, host, backend, _ = component()
    refresh = Mock()
    screen._refresh_radar = refresh
    with patch("controllers.weather.radar_replay_controller.threading.Thread") as thread:
        screen.request_enabled(True)
        thread.call_args.kwargs["target"]()
    backend.show_frames.assert_not_called()
    host.dispatch_ui.call_args.args[0]()
    backend.show_frames.assert_called_once_with(backend.load_frames.return_value)
    replays = host.schedule_ui_callback.call_args_list
    assert [call.args[0] for call in replays] == [300, 1200, 2500, 5000]
    replays[-1].args[1]()
    refresh.assert_called_once_with()


def test_seek_supersedes_pending_refresh() -> None:
    screen, host, backend, _ = component(True)
    with patch("controllers.weather.radar_replay_controller.threading.Thread") as thread:
        screen.request_enabled(True)
        thread.call_args.kwargs["target"]()
    screen.request_seek(2)
    host.dispatch_ui.call_args.args[0]()

    backend.select_frame.assert_called_once_with(2)
    backend.show_frames.assert_not_called()


def test_close_discards_queued_worker_failure() -> None:
    screen, host, backend, _ = component(True)
    backend.load_frames.side_effect = RuntimeError("unavailable")
    with patch("controllers.weather.radar_replay_controller.threading.Thread") as thread:
        screen.request_enabled(True)
        thread.call_args.kwargs["target"]()
    screen.close()
    host.dispatch_ui.call_args.args[0]()

    backend.hide.assert_not_called()
    backend.show_frames.assert_not_called()
