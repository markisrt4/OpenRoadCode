from apps.carUi.panel_manager_if import PanelManagerIf
from apps.carUi.weatherPanel import WeatherPanel
from apps.carUi.radio_panel_manager import (
    RadioPanelManager,
    RadioPanelConfig,
    RadioPanelTileConfig,
)


class WeatherPanelManager(PanelManagerIf):
    def __init__(self, app) -> None:
        super().__init__(app)
        self.noaa_panel_manager = None

    def show(self) -> None:
        if not self.prepare_panel("Weather"):
            return

        weather_view = WeatherPanel(
            self.content_frame,
            on_weather_dashboard_pressed=self.toggle_weather_dashboard,
            on_noaa_radio_pressed=self.show_noaa_weather_radio,
            create_tile=self.create_tile,
        )
        weather_view.pack(fill="both", expand=True)

        self.set_status("Weather menu ready")

    def toggle_weather_dashboard(self) -> None:
        try:
            running = self.app.weather_dash_launcher.toggle(
                remote_display=self.remote_display,
                set_status=self.set_status,
            )

            self.set_status(
                "Weather dashboard launched"
                if running
                else "Weather dashboard stopped"
            )

        except Exception as exc:
            self.set_status(f"Weather dashboard toggle failed: {exc}")
            print(f"[UI] Weather dashboard toggle error: {exc}")

    def show_noaa_weather_radio(self) -> None:
        if not self.prepare_panel("NOAA Weather Radio"):
            return

        manager = RadioPanelManager(
            parent=self.content_frame,
            create_tile=self.create_tile,
            radio_controller=self.app.weather_radio_controller,
            radio_app_launcher=self.app.weather_radio_launcher,
            panel_config=RadioPanelConfig(
                key="weather_radio",
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
                default_step_hz=self.app.weather_radio_config.default_mode.step_hz,
                default_mode_name=self.app.weather_radio_config.default_mode.name,
                preset_columns=2,
            ),
            remote_display=self.remote_display,
            set_status=self.set_status,
            on_frequency_changed=self.app.set_current_frequency,
        )

        manager.show()
        self.noaa_panel_manager = manager
