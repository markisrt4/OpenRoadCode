from dataclasses import dataclass
from typing import Optional

from apps.carUi.panel_manager_if import PanelManagerIf
from apps.carUi.scannerRadioPanel import ScannerRadioPanel, ScannerBandTileSpec
from apps.carUi.radio.radio_panel_config import RadioPanelConfig, RadioPanelTileConfig
from apps.carUi.radio.radio_panel_manager import RadioPanelManager


@dataclass(frozen=True)
class ScannerBandSpec:
    key: str
    icon: str
    title: str
    subtitle: str
    detail: str
    controller_attr: str
    launcher_attr: str
    config_attr: str


class ScannerPanelManager(PanelManagerIf):
    def __init__(self, app) -> None:
        super().__init__(app)

        self.active_radio_panel_manager: Optional[RadioPanelManager] = None

        self.bands = [
            ScannerBandSpec("police_fire", "PF", "POLICE / FIRE", "Public safety", "Local / regional monitoring", "police_fire_controller", "police_fire_launcher", "police_fire_config"),
            ScannerBandSpec("railroad",    "RR", "RAILROAD",      "Rail channels", "AAR road / dispatch",         "railroad_controller",    "railroad_launcher",    "railroad_config"   ),
            ScannerBandSpec("ham_2m",      "2M", "HAM 2m",        "144–148 MHz",   "Amateur VHF",                 "ham_2m_controller",      "ham_2m_launcher",      "ham_2m_config"     ),
            ScannerBandSpec("ham_70cm",    "70", "HAM 70cm",      "420–450 MHz",   "Amateur UHF",                 "ham_70cm_controller",    "ham_70cm_launcher",    "ham_70cm_config"   ),
            ScannerBandSpec("gmrs",        "GM", "GMRS",          "462 / 467 MHz", "Repeaters / simplex",         "gmrs_controller",        "gmrs_launcher",        "gmrs_config"       ),
            ScannerBandSpec("frs",         "FR", "FRS",           "462 / 467 MHz", "Family radios",               "frs_controller",         "frs_launcher",         "frs_config"        ),
            ScannerBandSpec("marine",      "⚓",  "MARINE",        "156 MHz",       "VHF marine band",             "marine_controller",      "marine_launcher",      "marine_config"     ),
            ScannerBandSpec("cb",          "CB", "CB",            "27 MHz AM",     "Citizens Band",               "cb_controller",          "cb_launcher",          "cb_config"         ),
            ]

    def show(self) -> None:
        if not self.prepare_panel("Scanner"):
            return

        self.app.set_panel_title("Scanner")
        self.active_radio_panel_manager = None

        panel = ScannerRadioPanel(
            parent=self.content_frame,
            bands=[
                ScannerBandTileSpec(
                    key=band.key,
                    icon=band.icon,
                    label=band.title,
                    subtitle=band.subtitle,
                    detail=band.detail,
                )
                for band in self.bands
            ],
            on_band_pressed=self.show_band_by_key,
            compact_ui=bool(getattr(self.app, "compact_ui", False)),
        )
        panel.pack(fill="both", expand=True)

    def show_band_by_key(self, key: str) -> None:
        band = self._find_band(key)

        if band is None:
            self.set_status(f"Unknown scanner band: {key}")
            return

        self.show_band(band)

    def show_band(self, band: ScannerBandSpec) -> None:
        try:
            radio_controller = getattr(self.app, band.controller_attr)
            radio_launcher   = getattr(self.app, band.launcher_attr)
            radio_config     = getattr(self.app, band.config_attr)
        except AttributeError as exc:
            self.set_status(f"{band.title} is not wired yet: {exc}")
            return

        self._clear_content()

        self.app.top_bar.set_back_command(self.show)
        self.app.top_bar.show_back_button()

        manager = RadioPanelManager(
            parent=self.content_frame,
            create_tile=self.create_tile,
            radio_controller=radio_controller,
            radio_app_launcher=radio_launcher,
            panel_config=RadioPanelConfig(
                key=band.key,
                title=band.title,
                launch_tile=RadioPanelTileConfig(
                    label="Launch SDR++",
                    subtitle=f"{band.title} receiver",
                    detail="Starts / toggles SDR++",
                ),
                radio_toggle_tile=RadioPanelTileConfig(
                    label="Radio ON/OFF",
                    subtitle="Radio control",
                    detail="Start / stop receiver",
                ),
                default_step_hz=radio_config.default_mode.step_hz,
                default_mode_name=radio_config.default_mode.name,
                preset_columns=2,
            ),
            remote_display=self.remote_display,
            set_status=self.set_status,
            on_frequency_changed=self.app.set_current_frequency,
        )

        manager.show()

        self.active_radio_panel_manager = manager
        self.app.set_panel_title(band.title)

    def _find_band(self, key: str) -> ScannerBandSpec | None:
        for band in self.bands:
            if band.key == key:
                return band
        return None

    def _clear_content(self) -> None:
        for child in self.content_frame.winfo_children():
            child.destroy()
