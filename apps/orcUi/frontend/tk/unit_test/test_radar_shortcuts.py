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
    assert panel._radar_button.configure.call_args.kwargs["text"] == "RADAR ON"
    panel._toggle_radar()
    assert shared["enabled"] is False
    assert panel._radar_button.configure.call_args.kwargs["text"] == "RADAR OFF"


def test_pending_radar_can_be_disabled_before_frame_finishes_loading():
    screen = object.__new__(NavigationScreen)
    screen._radar_controller = Mock()
    screen._radar_injection_controller = None
    screen._radar_enabled = False
    screen._panel = None
    with patch("apps.orcUi.frontend.tk.navigation_screen.threading.Thread") as thread:
        screen.set_radar_enabled(True)
        assert screen.radar_enabled
        load = thread.call_args.kwargs["target"]
        screen.set_radar_enabled(False)
        assert not screen.radar_enabled
        load()
    assert screen._radar_controller.hide.call_count == 2


def test_radar_menu_retains_actions_in_one_dropdown():
    panel = object.__new__(NavigationPanel)
    panel._theme_bundle = theme_bundle(ThemeMode.DARK)
    panel._radar_enabled = False
    panel._radar_palette = RadarPalette.UNIVERSAL
    panel._on_radar_toggle = Mock()
    panel._on_radar_previous = Mock()
    panel._on_radar_next = Mock()
    panel._on_radar_live = Mock()
    with patch.multiple("apps.orcUi.frontend.tk.navigation_radar_controls.tk",
                        Menubutton=Mock(), Menu=Mock(), BooleanVar=Mock()):
        # Avoid a Tcl interpreter; menu contents and callback wiring are asserted below.
        panel._render_radar_state = Mock()
        panel._build_radar_controls(Mock())
    commands = panel._radar_menu.add_command.call_args_list
    assert [call.kwargs["label"] for call in commands] == [
        "Previous frame", "Next frame", "Latest / live"
    ]
    commands[0].kwargs["command"]()
    panel._on_radar_previous.assert_called_once_with()
    assert panel._radar_menu.add_checkbutton.call_count == 2
