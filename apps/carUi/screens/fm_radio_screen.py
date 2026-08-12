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
from frontends.tk.radio import RadioPanel, RadioPanelConfig, RadioPanelTileConfig
from apps.carUi.radio.radio_session_controller import RadioSessionController
from ui.screen_ui_if import ScreenId
from frontends.tk.tk_screen_host_if import TkScreenHostIf


class FMRadioScreen(CarUiScreen):
    """Manage the FM radio panel and its radio session."""
    def __init__(
        self,
        host: TkScreenHostIf,
        *,
        runtime: Callable[[], RadioRuntime],
        remote_display: str,
        on_frequency_changed: Callable[[int], None],
        create_menu_tile: MenuTileFactory,
        binding_factory: RadioScreenBindingFactoryIf,
        back_action: Callable[[], None],
    ) -> None:
        super().__init__(host, ScreenId("fm_radio"), create_menu_tile)
        self._runtime = runtime
        self._remote_display = remote_display
        self._on_frequency_changed = on_frequency_changed
        self._binding_factory = binding_factory
        self._back_action = back_action
        self.fm_panel: Optional[RadioPanel] = None
        self.fm_session: Optional[RadioSessionController] = None

    def hide(self) -> None:
        if self.fm_panel is not None:
            self.fm_panel.stop_radio_status_polling()

    def show(self) -> None:
        if not self.prepare_screen("FM Radio", self._back_action):
            return

        runtime = self._runtime()
        panel_config = RadioPanelConfig(
            key=runtime.key,
            title="FM Radio",
            launch_tile=RadioPanelTileConfig(
                label="Launch SDR++",
                subtitle="FM receiver app",
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

        self.fm_session = binding.session
        self.fm_panel = binding.panel
        self.fm_panel.pack(fill="both", expand=True)
        self.fm_panel.start()
        self.fm_session.report_ready()
        self.set_title("FM Broadcast Radio")
