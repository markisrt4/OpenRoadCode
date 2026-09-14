# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

from collections.abc import Callable
from typing import Optional

from apps.carUi.runtime.car_ui_runtime import RadioRuntime
from apps.carUi.screens.car_ui_screen import CarUiScreen
from apps.carUi.screens.car_ui_screen_services import (
    MenuTileFactory,
    RadioScreenBindingFactoryIf,
)
from controllers.application_runtime import AppRuntimeManager
from frontends.tk.weather import WeatherMenuPanel
from frontends.tk.media.browser_return_overlay import BrowserReturnOverlay
from frontends.tk.radio import RadioPanel
from frontends.tk.radio.radio_panel_config import (
    RadioPanelConfig,
    RadioPanelTileConfig,
)
from apps.carUi.radio.radio_session_controller import RadioSessionController
from apps.common.uiTheme import WEATHER_PANEL_THEME
from ui.screen_ui_if import ScreenId
from frontends.tk.tk_screen_host_if import TkScreenHostIf


WEATHER_APP_KEY = "weather"


class WeatherScreen(CarUiScreen):
    """Coordinate the weather application and NOAA radio panel."""

    def __init__(
        self,
        host: TkScreenHostIf,
        *,
        weather_radio_runtime: Callable[[], RadioRuntime],
        app_runtime_manager: AppRuntimeManager | None,
        remote_display: str,
        auxiliary_display: str,
        on_frequency_changed: Callable[[int], None],
        create_menu_tile: MenuTileFactory,
        binding_factory: RadioScreenBindingFactoryIf,
        home_action: Callable[[], None],
    ) -> None:
        super().__init__(host, ScreenId("weather"), create_menu_tile)
        self._weather_radio_runtime = weather_radio_runtime
        self._app_runtime_manager = app_runtime_manager
        self._remote_display = remote_display
        self._auxiliary_display = auxiliary_display
        self._on_frequency_changed = on_frequency_changed
        self._binding_factory = binding_factory
        self._home_action = home_action
        self._return_overlay = BrowserReturnOverlay(
            self.content_frame,
            command=self._return_from_dashboard,
            background="#C62828",
            foreground="#FFFFFF",
            active_background="#8E0000",
        )
        self.noaa_panel: Optional[RadioPanel] = None
        self.noaa_session: Optional[RadioSessionController] = None

    def hide(self) -> None:
        if self.noaa_panel is not None:
            self.noaa_panel.stop_radio_status_polling()

    def show(self) -> None:
        if not self.prepare_screen("Weather", self._home_action):
            return

        weather_view = WeatherMenuPanel(
            parent=self.content_frame,
            on_weather_dashboard_pressed=self.toggle_weather_dashboard,
            on_noaa_radio_pressed=self.show_noaa_weather_radio,
            create_tile=self.create_tile,
            theme=WEATHER_PANEL_THEME,
        )
        weather_view.pack(fill="both", expand=True)
        self.set_status("Weather menu ready")

    def toggle_weather_dashboard(self) -> None:
        manager = self._app_runtime_manager
        if manager is None:
            self.set_status("Weather dashboard is disabled")
            return

        try:
            manager.launch(WEATHER_APP_KEY, self.set_status)
            self.set_status("Weather dashboard launched")
            self._return_overlay.show(
                x=12,
                y=12,
                display=self._auxiliary_display,
            )
        except Exception as exc:
            self.set_status(f"Weather dashboard toggle failed: {exc}")
            print(f"[UI] Weather dashboard toggle error: {exc}")

    def _return_from_dashboard(self) -> None:
        self._return_overlay.hide()
        manager = self._app_runtime_manager
        if manager is not None:
            manager.close(WEATHER_APP_KEY, self.set_status)
        self._home_action()

    def show_noaa_weather_radio(self) -> None:
        if not self.prepare_screen("NOAA Weather Radio", self.show):
            return
        runtime = self._weather_radio_runtime()

        panel_config = RadioPanelConfig(
            key=runtime.key,
            title="NOAA Weather Radio",
            launch_tile=RadioPanelTileConfig(
                label="Launch SDR++",
                subtitle="NOAA receiver app",
                detail="Starts / toggles SDR++",
            ),
            radio_toggle_tile=RadioPanelTileConfig(
                label="Radio ON/OFF",
                subtitle="Weather band control",
                detail="Start / stop receiver",
            ),
            default_step_hz=runtime.config.default_mode.step_hz,
            default_mode_name=runtime.config.default_mode.name,
            preset_columns=2,
        )

        binding = self._binding_factory(
            parent=self.content_frame,
            radio_controller=runtime.controller,
            radio_app_launcher=runtime.launcher,
            panel_config=panel_config,
            remote_display=self._remote_display,
            set_status=self.set_status,
            on_frequency_changed=self._on_frequency_changed,
        )

        self.noaa_session = binding.session
        self.noaa_panel = binding.panel
        self.noaa_panel.pack(fill="both", expand=True)
        self.noaa_panel.start()
        self.noaa_session.report_ready()
        self.set_title("NOAA Weather Radio")
