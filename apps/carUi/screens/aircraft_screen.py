# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

from collections.abc import Callable
from typing import Optional

from apps.carUi.runtime.car_ui_runtime import RadioRuntime
from apps.carUi.screens.car_ui_screen_services import (
    MenuTileFactory,
    RadioScreenBindingFactoryIf,
)
from apps.launchers.app_runtime_manager import AppRuntimeManager
from frontends.tk.aircraft import AircraftMenuPanel
from frontends.tk.media.browser_return_overlay import BrowserReturnOverlay
from apps.carUi.screens.car_ui_screen import CarUiScreen
from frontends.tk.radio import RadioPanel
from frontends.tk.radio.radio_panel_config import (
    RadioPanelConfig,
    RadioPanelTileConfig,
)
from apps.carUi.radio.radio_session_controller import RadioSessionController
from apps.common.uiTheme import AIRCRAFT_PANEL_THEME
from ui.screen_ui_if import ScreenId
from frontends.tk.tk_screen_host_if import TkScreenHostIf


ADSB_APP_KEY = "adsb"


class AircraftScreen(CarUiScreen):
    """Coordinate the Aircraft menu, ADS-B application, and Airband radio."""

    def __init__(
        self,
        host: TkScreenHostIf,
        *,
        airband_runtime: Callable[[], RadioRuntime],
        app_runtime_manager: AppRuntimeManager | None,
        remote_display: str,
        auxiliary_display: str,
        on_frequency_changed: Callable[[int], None],
        create_menu_tile: MenuTileFactory,
        binding_factory: RadioScreenBindingFactoryIf,
        home_action: Callable[[], None],
    ) -> None:
        super().__init__(host, ScreenId("aircraft"), create_menu_tile)
        self._airband_runtime = airband_runtime
        self._app_runtime_manager = app_runtime_manager
        self._remote_display = remote_display
        self._auxiliary_display = auxiliary_display
        self._on_frequency_changed = on_frequency_changed
        self._binding_factory = binding_factory
        self._home_action = home_action
        self._return_overlay = BrowserReturnOverlay(
            self.content_frame,
            command=self._return_from_adsb,
            background="#C62828",
            foreground="#FFFFFF",
            active_background="#8E0000",
        )
        self.airband_panel: Optional[RadioPanel] = None
        self.airband_session: Optional[RadioSessionController] = None

    def hide(self) -> None:
        if self.airband_panel is not None:
            self.airband_panel.stop_radio_status_polling()

    def show(self) -> None:
        if not self.prepare_screen("Aircraft", self._home_action):
            return

        panel = AircraftMenuPanel(
            parent=self.content_frame,
            on_adsb_pressed=self.launch_adsb,
            on_airband_pressed=self.show_airband_am,
            create_tile=self.create_tile,
            theme=AIRCRAFT_PANEL_THEME,
        )
        panel.pack(fill="both", expand=True)

        self.set_status("Aircraft menu ready")

    def launch_adsb(self) -> None:
        manager = self._app_runtime_manager
        if manager is None:
            self.set_status("ADS-B is disabled")
            return

        try:
            manager.launch(ADSB_APP_KEY, self.set_status)
            self.set_status("ADS-B dashboard launched")
            self._return_overlay.show(
                x=12,
                y=12,
                display=self._auxiliary_display,
            )
        except Exception as exc:
            self.set_status(f"ADS-B toggle failed: {exc}")
            print(f"[UI] ADS-B toggle error: {exc}")

    def _return_from_adsb(self) -> None:
        self._return_overlay.hide()
        manager = self._app_runtime_manager
        if manager is not None:
            manager.close(ADSB_APP_KEY, self.set_status)
        self._home_action()

    def show_airband_am(self) -> None:
        if not self.prepare_screen("Airband AM", self.show):
            return
        runtime = self._airband_runtime()

        panel_config = RadioPanelConfig(
            key=runtime.key,
            title="Airband AM",
            launch_tile=RadioPanelTileConfig(
                label="Launch SDR++",
                subtitle="Airband AM receiver",
                detail="Starts / toggles SDR++",
            ),
            radio_toggle_tile=RadioPanelTileConfig(
                label="Radio ON/OFF",
                subtitle="Radio control",
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

        self.airband_session = binding.session
        self.airband_panel = binding.panel
        self.airband_panel.pack(fill="both", expand=True)
        self.airband_panel.start()
        self.airband_session.report_ready()

        self.set_title("Airband AM Radio")
