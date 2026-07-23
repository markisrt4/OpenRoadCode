from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from apps.carUi.panels.panel_manager_if import PanelManagerIf
from apps.carUi.panels.scanner_radio_panel import ScannerBandTileSpec, ScannerRadioPanel
from apps.carUi.radio.radio_panel import RadioPanel
from apps.carUi.radio.radio_panel_config import RadioPanelConfig, RadioPanelTileConfig
from apps.carUi.radio.radio_panel_factory import create_radio_panel_binding
from apps.carUi.radio.radio_session_controller import RadioSessionController


@dataclass(frozen=True)
class ScannerBandSpec:
    """Describe one scanner band shown in the scanner menu."""
    key: str
    icon: str
    title: str
    subtitle: str
    detail: str


class ScannerPanelManager(PanelManagerIf):
    """Build scanner-band menus and manage the selected radio session."""
    def __init__(self, app) -> None:
        super().__init__(app)
        self.active_radio_panel: Optional[RadioPanel] = None
        self.active_radio_session: Optional[RadioSessionController] = None
        self.bands = (
            ScannerBandSpec("police_fire", "PF", "POLICE / FIRE", "Public safety", "Local / regional monitoring"),
            ScannerBandSpec("railroad", "RR", "RAILROAD", "Rail channels", "AAR road / dispatch"),
            ScannerBandSpec("ham_2m", "2M", "HAM 2m", "144–148 MHz", "Amateur VHF"),
            ScannerBandSpec("ham_70cm", "70", "HAM 70cm", "420–450 MHz", "Amateur UHF"),
            ScannerBandSpec("gmrs", "GM", "GMRS", "462 / 467 MHz", "Repeaters / simplex"),
            ScannerBandSpec("frs", "FR", "FRS", "462 / 467 MHz", "Family radios"),
            ScannerBandSpec("marine", "⚓", "MARINE", "156 MHz", "VHF marine band"),
            ScannerBandSpec("cb", "CB", "CB", "27 MHz AM", "Citizens Band"),
        )

    def show(self) -> None:
        """Display the configured scanner-band menu."""
        if not self.prepare_panel("Scanner"):
            return

        self.app.top_bar.set_back_command(lambda: self.app.show_menu("radio"))
        self.active_radio_panel = None
        self.active_radio_session = None

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
                if band.key in self.app.runtime.radios
            ],
            on_band_pressed=self.show_band_by_key,
            create_tile=self.create_tile,
            compact_ui=bool(getattr(self.app, "compact_ui", False)),
        )
        panel.pack(fill="both", expand=True)
        self.set_status("Scanner ready")

    def show_band_by_key(self, key: str) -> None:
        """Open a scanner band identified by its stable key."""
        band = self._find_band(key)
        if band is None:
            self.set_status(f"Unknown scanner band: {key}")
            return

        self.show_band(band)

    def show_band(self, band: ScannerBandSpec) -> None:
        """Open and start the radio panel for ``band``."""
        runtime = self.app.runtime.radios.get(band.key)

        self._clear_content()
        self.app.top_bar.set_back_command(self.show)
        self.app.top_bar.show_back_button()

        panel_config = RadioPanelConfig(
            key=runtime.key,
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

        self.active_radio_session = binding.session
        self.active_radio_panel = binding.panel
        self.active_radio_panel.pack(fill="both", expand=True)
        self.active_radio_panel.start()
        self.active_radio_session.report_ready()
        self.set_title(band.title)

    def _find_band(self, key: str) -> ScannerBandSpec | None:
        for band in self.bands:
            if band.key == key:
                return band
        return None

    def _clear_content(self) -> None:
        for child in self.content_frame.winfo_children():
            child.destroy()
