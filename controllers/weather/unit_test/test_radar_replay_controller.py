# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Replay selections and timer lifecycle without network or native rendering."""

from unittest.mock import Mock

import pytest

from controllers.weather.radar_replay_controller import RadarReplayController
from ui.weather.radar_ui_stub import RadarUiStub
from controllers.weather import RadarFrame, WeatherRadarController


@pytest.fixture
def screen():
    provider = Mock()
    provider.get_frames.return_value = tuple(
        RadarFrame(timestamp=t, tile_url=f"https://example.test/{t}/{{z}}/{{x}}/{{y}}.png")
        for t in (100, 200, 300)
    )
    controller = WeatherRadarController(provider, Mock())
    controller.show_latest()
    screen = RadarReplayController(Mock(), RadarUiStub(), controller)
    screen.request_navigation_visible(True)
    return screen


def test_play_loops_cached_history_without_network(screen):
    screen._radar_play_pause()
    assert screen._radar_controller.frame_index == 0
    for expected in (1, 2, 0):
        callback = screen._host.schedule_ui_callback.call_args.args[1]
        callback()
        assert screen._radar_controller.frame_index == expected
    screen._radar_controller._provider.get_frames.assert_called_once()


def test_scrubbing_pauses_and_invalidates_pending_playback(screen):
    screen._radar_play_pause()
    old_tick = screen._host.schedule_ui_callback.call_args.args[1]
    screen._radar_seek(2)
    old_tick()
    assert not screen._radar_playing
    assert screen._radar_controller.frame_index == 2


def test_rapid_pause_and_resume_does_not_create_two_timer_loops(screen):
    screen._radar_play_pause()
    old_tick = screen._host.schedule_ui_callback.call_args.args[1]
    screen._radar_play_pause()
    screen._radar_play_pause()
    calls = screen._host.schedule_ui_callback.call_count
    old_tick()
    assert screen._host.schedule_ui_callback.call_count == calls
    screen._host.schedule_ui_callback.call_args.args[1]()
    assert screen._radar_controller.frame_index == 1


@pytest.mark.parametrize("action", ["hide", "off", "live"])
def test_playback_stops_on_navigation_visibility_or_live(screen, action):
    screen._radar_play_pause()
    old_tick = screen._host.schedule_ui_callback.call_args.args[1]
    if action == "hide":
        screen.request_navigation_visible(False)
    elif action == "off":
        screen._toggle_radar(False)
    else:
        screen._toggle_radar = Mock()
        screen._radar_live()
        screen._toggle_radar.assert_called_once_with(True)
    calls = screen._host.schedule_ui_callback.call_count
    old_tick()
    assert not screen._radar_playing
    assert screen._host.schedule_ui_callback.call_count == calls


def test_speed_changes_next_timer_interval(screen):
    screen._radar_set_speed(2.0)
    screen._radar_play_pause()
    assert screen._host.schedule_ui_callback.call_args.args[0] == 750


def test_invalid_timeline_index_does_not_publish_frame(screen):
    controller = screen._radar_controller
    before = controller._map_renderer.set_weather_radar.call_count
    with pytest.raises(IndexError):
        controller.select_frame(-1)
    with pytest.raises(IndexError):
        controller.select_frame(3)
    assert controller._map_renderer.set_weather_radar.call_count == before


def test_old_source_download_and_error_cannot_replace_new_source(screen):
    screen._radar_load_generation = 2
    before = screen._radar_controller._map_renderer.set_weather_radar.call_count
    screen._show_radar_frames((RadarFrame(999, "https://old-source.test/tile.png"),), 1)
    screen._radar_load_failed("old source timed out", 1)
    assert screen._radar_enabled
    assert screen._radar_controller.frame_time == 300
    assert screen._radar_controller._map_renderer.set_weather_radar.call_count == before


def test_forecast_waits_for_tiles_before_starting_display_interval(screen):
    controller = screen._radar_controller
    controller._provider.provider_id = "hrrr"
    controller._tile_service = Mock()
    controller._tile_service.frame_error.return_value = None
    controller._tile_service.frame_ready.return_value = False
    screen._radar_play_pause()
    screen._host.schedule_ui_callback.call_args.args[1]()
    assert controller.frame_index == 0
    assert screen._host.schedule_ui_callback.call_args.args[0] == 250
    assert screen._ui.state.loading
    controller._tile_service.frame_ready.return_value = True
    screen._host.schedule_ui_callback.call_args.args[1]()
    assert controller.frame_index == 0
    assert screen._host.schedule_ui_callback.call_args.args[0] == 1500
    screen._host.schedule_ui_callback.call_args.args[1]()
    assert controller.frame_index == 1
    assert screen._host.schedule_ui_callback.call_args.args[0] == 100


def test_forecast_tile_failure_pauses_with_explanation(screen):
    controller = screen._radar_controller
    controller._provider.provider_id = "hrrr"
    controller._tile_service = Mock()
    controller._tile_service.frame_error.return_value = "download failed"
    screen._radar_play_pause()
    screen._host.schedule_ui_callback.call_args.args[1]()
    assert not screen._radar_playing
    assert screen._ui.state.status == "Forecast radar loading failed: download failed"


def test_paused_forecast_does_not_resume_waiting_callback(screen):
    screen._radar_controller._provider.provider_id = "hrrr"
    screen._radar_play_pause()
    callback = screen._host.schedule_ui_callback.call_args.args[1]
    screen._pause_radar()
    calls = screen._host.schedule_ui_callback.call_count
    callback()
    assert screen._host.schedule_ui_callback.call_count == calls


def test_old_history_completion_cannot_overwrite_new_source(screen):
    screen._radar_load_generation = 2
    selector = Mock()
    before = screen._radar_controller.frame_time
    screen._complete_radar_selection(selector, (RadarFrame(999, 'https://old.test/tile'),), 1)
    assert screen._radar_controller.frame_time == before
    selector.assert_not_called()


def test_closed_replay_rejects_a_completed_download(screen):
    screen.close()
    before = screen._radar_controller._map_renderer.set_weather_radar.call_count
    screen._show_radar_frames((RadarFrame(999, 'https://old.test/tile'),), screen._radar_load_generation)
    assert screen._radar_controller._map_renderer.set_weather_radar.call_count == before
