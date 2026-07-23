from __future__ import annotations

from typing import Optional

from apps.carUi.panels.panel_manager_if import PanelManagerIf
from apps.carUi.radio.radio_panel import RadioPanel
from apps.carUi.radio.radio_panel_config import RadioPanelConfig, RadioPanelTileConfig
from apps.carUi.radio.radio_panel_factory import create_radio_panel_binding
from apps.carUi.radio.radio_session_controller import RadioSessionController


class FMRadioPanelManager(PanelManagerIf):
    """Manage the FM radio panel and its radio session."""
    def __init__(self, app) -> None:
        super().__init__(app)
        self.fm_panel: Optional[RadioPanel] = None
        self.fm_session: Optional[RadioSessionController] = None

    def show(self) -> None:
        if not self.prepare_panel("FM Radio"):
            return

        runtime = self.app.runtime.radios.get("fm_radio")
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

        binding = create_radio_panel_binding(
            parent=self.content_frame,
            radio_controller=runtime.controller,
            radio_app_launcher=runtime.launcher,
            panel_config=panel_config,
            remote_display=self.remote_display,
            set_status=self.set_status,
            on_frequency_changed=(
                self.app.vehicle_status_manager.set_frequency
            ),
        )

        self.fm_session = binding.session
        self.fm_panel = binding.panel
        self.fm_panel.pack(fill="both", expand=True)
        self.fm_panel.start()
        self.fm_session.report_ready()
        self.set_title("FM Broadcast Radio")
