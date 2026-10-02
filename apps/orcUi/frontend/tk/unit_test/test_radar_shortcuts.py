# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Radar shortcut and menu behavior without a display or network."""

from unittest.mock import Mock, patch

from apps.orcUi.frontend.tk.home_map_panel import HomeMapPanel
from apps.orcUi.frontend.tk.navigation_screen import NavigationScreen
from apps.orcUi.frontend.tk.navigation_panel import NavigationPanel
from apps.orcUi.theme_runtime import theme_bundle
from controllers.weather.radar_palette import RadarPalette
from frontends.tk.weather.orc_weather_panel import OrcWeatherPanel
from ui.theme import ThemeMode


def test_weather_radar_button_calls_navigation_action():
    panel = object.__new__(OrcWeatherPanel)
    panel._on_radar_map = Mock()
    panel._request_radar_map()
    panel._on_radar_map.assert_called_once_with()


def test_home_toggle_uses_shared_state_and_updates_label():
    panel = object.__new__(HomeMapPanel)
    shared = {"enabled": False}
    panel._radar_enabled = lambda: shared["enabled"]
    panel._on_radar_toggle = lambda enabled: shared.update(enabled=enabled)
    panel._radar_button = Mock()
    panel._theme = theme_bundle(ThemeMode.DARK)
    panel._toggle_radar()
    assert shared["enabled"] is True
    assert panel._radar_button.configure.call_args.kwargs["text"] == "☁ ON"
    panel._toggle_radar()
    assert shared["enabled"] is False
    assert panel._radar_button.configure.call_args.kwargs["text"] == "☁ OFF"


def test_pending_radar_can_be_disabled_before_frame_finishes_loading():
    screen = object.__new__(NavigationScreen)
    screen._radar_controller = Mock()
    screen._radar_injection_controller = None
    screen._radar_enabled = False
    screen._panel = None
    screen._host = Mock()
    screen._on_radar_visibility_changed = None
    with patch("apps.orcUi.frontend.tk.navigation_screen.threading.Thread") as thread:
        screen.set_radar_enabled(True)
        assert screen.radar_enabled
        load = thread.call_args.kwargs["target"]
        screen.set_radar_enabled(False)
        assert not screen.radar_enabled
        load()
    completed = screen._host.schedule_ui_callback.call_args.args[1]
    completed()
    screen._radar_controller.show_frames.assert_not_called()
    screen._radar_controller.hide.assert_called_once_with()


def test_radar_menu_opens_collapsible_timeline_and_keeps_cloud_toggle():
    panel = object.__new__(NavigationPanel)
    panel._theme_bundle = theme_bundle(ThemeMode.DARK)
    panel._radar_enabled = False
    panel._radar_palette = RadarPalette.UNIVERSAL
    panel._on_radar_toggle = Mock()
    panel._on_radar_previous = Mock()
    panel._on_radar_next = Mock()
    panel._on_radar_live = Mock()
    panel._on_radar_play = Mock()
    panel._on_radar_seek = Mock()
    panel._on_radar_speed = Mock()
    panel._radar_speed = 1.0
    with patch.multiple("apps.orcUi.frontend.tk.navigation_radar_controls.tk",
                        Menubutton=Mock(), Menu=Mock(), BooleanVar=Mock(), Button=Mock()):
        # Avoid a Tcl interpreter; menu contents and callback wiring are asserted below.
        panel._render_radar_state = Mock()
        panel._build_radar_controls(Mock())
    with patch("apps.orcUi.frontend.tk.navigation_radar_controls.RadarReplayPanel") as popup:
        panel._toggle_radar_menu()
        callbacks = popup.call_args.kwargs
        callbacks["on_play"]()
        callbacks["on_seek"](3)
        callbacks["on_live"]()
        panel._on_radar_play.assert_called_once_with()
        panel._on_radar_seek.assert_called_once_with(3)
        panel._on_radar_live.assert_called_once_with()
        panel._toggle_radar_menu()
        popup.return_value.destroy.assert_called_once_with()
        assert panel._radar_replay_panel is None


def test_cloud_toggle_reflects_visibility_without_changing_camera():
    panel = object.__new__(NavigationPanel)
    panel._theme_bundle = theme_bundle(ThemeMode.DARK)
    panel._radar_button = Mock()
    panel._radar_quick_toggle = Mock()
    panel._radar_enabled = False
    panel._radar_frame_time = None
    panel._on_radar_toggle = Mock()
    panel._request_handler = Mock()
    panel._render_radar_state()
    off = panel._radar_quick_toggle.configure.call_args.kwargs["fg"]
    panel._toggle_radar()
    on = panel._radar_quick_toggle.configure.call_args.kwargs["fg"]
    assert off != on
    panel._request_handler.request_zoom.assert_not_called()
    panel._on_radar_toggle.assert_called_once_with(True)


def test_failed_download_resets_both_screens_and_reports_error():
    screen = object.__new__(NavigationScreen)
    screen._radar_enabled = True
    screen._radar_controller = Mock()
    screen._panel = Mock()
    screen._host = Mock()
    screen._on_radar_visibility_changed = Mock()
    screen._radar_load_failed("provider timed out")
    assert screen.radar_enabled is False
    assert screen._panel._radar_enabled is False
    screen._radar_controller.hide.assert_called_once_with()
    screen._on_radar_visibility_changed.assert_called_once_with()
    screen._host.set_screen_status.assert_called_once_with("Radar unavailable: provider timed out")


def test_download_presents_on_ui_thread_and_retries_slow_renderer():
    screen = object.__new__(NavigationScreen)
    screen._radar_enabled = False
    screen._radar_controller = Mock()
    screen._radar_injection_controller = None
    screen._on_radar_visibility_changed = None
    screen._panel = None
    screen._host = Mock()
    screen._refresh_radar = Mock()
    with patch("apps.orcUi.frontend.tk.navigation_screen.threading.Thread") as thread:
        screen.set_radar_enabled(True)
        thread.call_args.kwargs["target"]()
    screen._radar_controller.show_frames.assert_not_called()
    screen._host.schedule_ui_callback.call_args.args[1]()
    screen._radar_controller.show_frames.assert_called_once_with(
        screen._radar_controller.load_frames.return_value)
    replays = screen._host.schedule_ui_callback.call_args_list[1:]
    assert [call.args[0] for call in replays] == [300, 1200, 2500, 5000]
    replays[-1].args[1]()
    screen._refresh_radar.assert_called_once_with()
