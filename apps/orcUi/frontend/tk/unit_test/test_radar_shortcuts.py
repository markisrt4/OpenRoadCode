# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Radar shortcut and menu behavior without a display or network."""

from unittest.mock import Mock, patch

from apps.orcUi.frontend.tk.home_map_panel import HomeMapPanel
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
    panel._on_radar_source = Mock()
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


def test_weather_state_renders_provider_role_and_current_temperature():
    from common.units.unit_system import UnitSystem
    from ui.weather.weather_ui_if import WeatherCurrentUiState, WeatherUiState
    panel = object.__new__(OrcWeatherPanel)
    panel._theme_bundle = lambda: theme_bundle(ThemeMode.DARK)
    panel._unit_system = lambda: UnitSystem.IMPERIAL
    for name in ('_location', '_provider_label', '_symbol', '_temperature', '_condition', '_summary'):
        setattr(panel, name, Mock())
    panel._metric_cards = [(None, None, Mock()) for _ in range(3)]
    panel._render_forecasts = Mock()
    panel.set_weather_state(WeatherUiState(
        location_name='Detroit', provider_label='Open-Meteo', fetched_at=1000,
        current=WeatherCurrentUiState(temperature_k=283.15)))
    assert panel._provider_label.configure.call_args.kwargs['text'].startswith('Weather data provider: Open-Meteo')
    assert panel._temperature.configure.call_args.kwargs['text'] == '50°F'
    panel._render_forecasts.assert_called_once()
