from apps.carUi.panel_manager_if import PanelManagerIf

from apps.carUi.radio.radio_panel_manager import (
    RadioPanelManager,
)

from apps.carUi.radio.radio_panel_config import (
    RadioPanelConfig,
    RadioPanelTileConfig,
)


class FMRadioPanelManager(PanelManagerIf):
    def __init__(self, app) -> None:
        super().__init__(app)
        self.fm_panel_manager = None

    def show(self) -> None:
        if not self.prepare_panel("FM Radio"):
            return

        manager = RadioPanelManager(
            parent=self.content_frame,
            create_tile=self.create_tile,
            radio_controller=self.app.fm_radio_controller,
            radio_app_launcher=self.app.fm_radio_launcher,
            panel_config=RadioPanelConfig(
                key="fm",
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
                default_step_hz=self.app.fm_radio_config.default_mode.step_hz,
                default_mode_name=self.app.fm_radio_config.default_mode.name,
                preset_columns=2,
            ),
            remote_display=self.remote_display,
            set_status=self.set_status,
            on_frequency_changed=self.app.set_current_frequency,
        )

        manager.show()
        self.fm_panel_manager = manager
        self.app.set_panel_title("FM Broadcast Radio")
  