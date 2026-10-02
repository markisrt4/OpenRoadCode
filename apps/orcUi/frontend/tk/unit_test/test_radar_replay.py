# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Replay selections and timer lifecycle without network or native rendering."""

from unittest.mock import Mock

import pytest

from apps.orcUi.frontend.tk.navigation_screen import NavigationScreen
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
    screen = object.__new__(NavigationScreen)
    screen._radar_controller = controller
    screen._radar_enabled = True
    screen._radar_playing = False
    screen._radar_playback_generation = 0
    screen._radar_playback_speed = 1.0
    screen._panel = Mock()
    screen._host = Mock()
    screen._map_runtime = Mock()
    screen._on_radar_visibility_changed = None
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
        screen.hide()
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
