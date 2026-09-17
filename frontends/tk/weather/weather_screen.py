# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Contract-based native Weather screen for orcUi."""

from __future__ import annotations

from collections.abc import Callable
import threading

from common.units import UnitSystem
from controllers.weather import WeatherController, WeatherPresenter
from frontends.tk.tk_screen import TkScreen
from frontends.tk.tk_screen_host_if import TkScreenHostIf
from ui.screen_ui_if import ScreenId
from ui.theme import ThemeBundle, ThemeMode
from ui.weather import WeatherRequestHandlerIf

from .orc_weather_panel import OrcWeatherPanel


class WeatherScreen(TkScreen, WeatherRequestHandlerIf):
    """Own native Weather presentation and asynchronous forecast refresh."""

    def __init__(
        self,
        host: TkScreenHostIf,
        *,
        controller: WeatherController,
        theme_bundle: Callable[[], ThemeBundle],
        unit_system: Callable[[], UnitSystem] = lambda: UnitSystem.IMPERIAL,
    ) -> None:
        super().__init__(ScreenId("weather"))
        self._host = host
        self._controller = controller
        self._theme_bundle = theme_bundle
        self._unit_system = unit_system
        self._panel: OrcWeatherPanel | None = None
        self._presenter: WeatherPresenter | None = None
        self._generation = 0

    def show(self) -> None:
        self.hide()
        self._host.activate_screen(self)
        self._host.clear_screen_content()
        self._host.set_screen_title("WEATHER")
        panel = OrcWeatherPanel(
            self._host.screen_parent,
            theme_bundle=self._theme_bundle,
            unit_system=self._unit_system,
        )
        panel.pack(fill="both", expand=True)
        panel.set_weather_request_handler(self)
        self._panel = panel
        self._presenter = WeatherPresenter(panel)
        latest = self._controller.latest()
        if latest is not None:
            self._presenter.present(latest)
        self.request_refresh()

    def hide(self) -> None:
        self._generation += 1
        if self._panel is not None:
            self._panel.set_weather_request_handler(None)
        self._panel = None
        self._presenter = None

    def request_refresh(self) -> None:
        self._generation += 1
        generation = self._generation
        self._host.set_screen_status("Weather: refreshing")
        threading.Thread(target=self._refresh, args=(generation,), daemon=True).start()

    def set_theme_mode(self, mode: ThemeMode) -> None:
        del mode
        panel = self._panel
        if panel is not None and panel.winfo_exists():
            panel.set_theme_bundle(self._theme_bundle())

    def _refresh(self, generation: int) -> None:
        try:
            state = self._controller.refresh_if_stale(300.0)
        except Exception as error:
            detail = str(error)
            self._host.schedule_ui_callback(
                0,
                lambda detail=detail: self._refresh_failed(generation, detail),
            )
            return
        self._host.schedule_ui_callback(
            0,
            lambda state=state: self._refresh_succeeded(generation, state),
        )

    def _refresh_succeeded(self, generation: int, state) -> None:
        if generation != self._generation or self._presenter is None:
            return
        self._presenter.present(state)
        self._host.set_screen_status("")

    def _refresh_failed(self, generation: int, detail: str) -> None:
        if generation != self._generation:
            return
        self._host.set_screen_status(f"Weather: {detail}")
