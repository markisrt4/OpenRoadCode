from apps.carUi.aircraft_panel import AircraftPanel
from apps.carUi.panel_manager_if import PanelManagerIf

from apps.carUi.radio.radio_panel_manager import (
    RadioPanelManager,
)

from apps.carUi.radio.radio_panel_config import (
    RadioPanelConfig,
    RadioPanelTileConfig,
)

class AircraftPanelManager(PanelManagerIf):
    def __init__(self, app) -> None:
        super().__init__(app)
        self.airband_panel_manager = None

    def show(self) -> None:
        if not self.prepare_panel("Aircraft"):
            return

        aircraft_view = AircraftPanel(
            self.content_frame,
            on_adsb_pressed=self.launch_adsb,
            on_airband_pressed=self.show_airband_am,
            create_tile=self.create_tile,
        )
        aircraft_view.pack(fill="both", expand=True)
        self.set_status("Aircraft menu ready")

    def launch_adsb(self) -> None:
        try:
            running = self.app.adsb_launcher.toggle(
                remote_display=self.remote_display,
                set_status=self.set_status,
            )

            self.set_status(
                "ADS-B dashboard launched"
                if running
                else "ADS-B dashboard stopped"
            )

        except Exception as exc:
            self.set_status(f"ADS-B toggle failed: {exc}")
            print(f"[UI] ADS-B toggle error: {exc}")

    def show_airband_am(self) -> None:
        if not self.prepare_panel("Airband AM"):
            return

        manager = RadioPanelManager(
            parent=self.content_frame,
            create_tile=self.create_tile,
            radio_controller=self.app.airband_radio_controller,
            radio_app_launcher=self.app.airband_radio_launcher,
            panel_config=RadioPanelConfig(
                key="airband",
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
                default_step_hz=self.app.airband_radio_config.default_mode.step_hz,
                default_mode_name=self.app.airband_radio_config.default_mode.name,
                preset_columns=2,
            ),
            remote_display=self.remote_display,
            set_status=self.set_status,
            on_frequency_changed=self.app.set_current_frequency,
        )

        manager.show()
        self.airband_panel_manager = manager
        self.app.set_panel_title("Airband AM Radio")
