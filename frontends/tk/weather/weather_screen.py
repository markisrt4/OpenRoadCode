# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Contract-based native Weather screen for orcUi."""

from __future__ import annotations

from collections.abc import Callable

from common.units import UnitSystem
from frontends.tk.tk_screen import TkScreen
from frontends.tk.tk_screen_host_if import TkScreenHostIf
from ui.screen_ui_if import ScreenId
from ui.theme import ThemeBundle, ThemeMode
from ui.weather import WeatherRequestHandlerIf, WeatherUiState
from ui.weather.weather_screen_ui_if import WeatherScreenUiIf, WeatherScreenRequestHandlerIf

from .orc_weather_panel import OrcWeatherPanel


class WeatherScreen(TkScreen, WeatherScreenUiIf):
    """Present native Weather through toolkit-independent state and requests."""

    def __init__(
        self,
        host: TkScreenHostIf,
        *,
        theme_bundle: Callable[[], ThemeBundle],
        unit_system: Callable[[], UnitSystem] = lambda: UnitSystem.IMPERIAL,
        on_weather_radio: Callable[[], None] | None = None,
        on_radar_map: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(ScreenId("weather"))
        self._online = True
        self._host = host
        self._theme_bundle = theme_bundle
        self._unit_system = unit_system
        self._on_weather_radio = on_weather_radio
        self._on_radar_map = on_radar_map
        self._panel: OrcWeatherPanel | None = None
        self._handler: WeatherScreenRequestHandlerIf | None = None
        self._state: WeatherUiState | None = None

    def show(self) -> None:
        self.hide()
        self._host.activate_screen(self)
        self._host.clear_screen_content()
        self._host.set_screen_title("WEATHER")
        panel = OrcWeatherPanel(
            self._host.screen_parent,
            theme_bundle=self._theme_bundle,
            unit_system=self._unit_system,
            on_weather_radio=self._on_weather_radio,
            on_radar_map=self._on_radar_map,
        )
        panel.pack(fill="both", expand=True)
        panel.set_weather_request_handler(self._handler)
        self._panel = panel
        panel.set_online(self._online)
        panel.set_weather_state(self._state)
        if self._handler is not None:
            self._handler.set_visible(True)

    def hide(self) -> None:
        if self._handler is not None:
            self._handler.set_visible(False)
        if self._panel is not None:
            self._panel.set_weather_request_handler(None)
        self._panel = None

    def set_weather_request_handler(self, handler: WeatherRequestHandlerIf | None) -> None:
        """Bind forecast requests. @param handler Lifecycle handler or None."""
        if handler is not None and not isinstance(handler, WeatherScreenRequestHandlerIf):
            raise TypeError("Weather screen requires WeatherScreenRequestHandlerIf")
        self._handler = handler
        if self._panel is not None:
            self._panel.set_weather_request_handler(handler)

    def set_weather_state(self, state: WeatherUiState | None) -> None:
        """Display SI forecast state. @param state Latest forecast or None."""
        self._state = state
        if self._panel is not None:
            self._panel.set_weather_state(state)

    def set_online(self, online: bool) -> None:
        """Present availability. @param online Whether internet actions are enabled."""
        self._online = online
        if self._panel is not None:
            self._panel.set_online(online)

    def set_loading(self, loading: bool) -> None:
        """Display refresh progress. @param loading Whether refresh is pending."""
        if self._panel is not None:
            self._panel.set_loading(loading)

    def set_weather_status(self, status: str) -> None:
        """Display refresh status. @param status Human-readable status."""
        if self._panel is not None:
            self._host.set_screen_status(status)

    def set_theme_mode(self, mode: ThemeMode) -> None:
        del mode
        panel = self._panel
        if panel is not None and panel.winfo_exists():
            panel.set_theme_bundle(self._theme_bundle())
