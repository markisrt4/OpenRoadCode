from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Callable
from typing import Optional

from apps.carUi.runtime.radio_runtime_registry import RadioRuntimeRegistry
from apps.carUi.screens.car_ui_screen import CarUiScreen
from apps.carUi.screens.car_ui_screen_services import (
    MenuTileFactory,
    RadioScreenBindingFactoryIf,
)
from frontends.tk.radio import (
    ScannerBandSelectionPanel,
    ScannerBandTileSpec,
)
from frontends.tk.radio import RadioPanel, RadioPanelConfig, RadioPanelTileConfig
from apps.carUi.radio.radio_session_controller import RadioSessionController
from apps.common.uiTheme import COLORS, MENU_TILE_STYLE
from ui.screen_ui_if import ScreenId
from frontends.tk.tk_screen_host_if import TkScreenHostIf


@dataclass(frozen=True)
class ScannerBandSpec:
    """Describe one scanner band shown in the scanner menu."""
    key: str
    icon: str
    title: str
    subtitle: str
    detail: str


class ScannerScreen(CarUiScreen):
    """Build scanner-band menus and manage the selected radio session."""
    def __init__(
        self,
        host: TkScreenHostIf,
        *,
        radio_runtimes: RadioRuntimeRegistry,
        remote_display: str,
        on_frequency_changed: Callable[[int], None],
        create_menu_tile: MenuTileFactory,
        binding_factory: RadioScreenBindingFactoryIf,
        radio_menu_action: Callable[[], None],
        compact_ui: bool,
    ) -> None:
        super().__init__(host, ScreenId("scanner_radio"), create_menu_tile)
        self._radio_runtimes = radio_runtimes
        self._remote_display = remote_display
        self._on_frequency_changed = on_frequency_changed
        self._binding_factory = binding_factory
        self._radio_menu_action = radio_menu_action
        self._compact_ui = compact_ui
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

    def hide(self) -> None:
        if self.active_radio_panel is not None:
            self.active_radio_panel.stop_radio_status_polling()

    def show(self) -> None:
        """Display the configured scanner-band menu."""
        if not self.prepare_screen("Scanner", self._radio_menu_action):
            return
        self.active_radio_panel = None
        self.active_radio_session = None

        panel = ScannerBandSelectionPanel(
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
                if band.key in self._radio_runtimes
            ],
            on_band_pressed=self.show_band_by_key,
            create_tile=self.create_tile,
            theme={
                "colors": {"background": COLORS["app_bg"]},
                "profiles": MENU_TILE_STYLE,
            },
            compact_ui=self._compact_ui,
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
        runtime = self._radio_runtimes.get(band.key)

        self.host.clear_screen_content()
        self.host.set_screen_back_action(self.show)

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

        binding = self._binding_factory(
            parent=self.content_frame,
            radio_controller=runtime.controller,
            radio_app_launcher=runtime.launcher,
            panel_config=panel_config,
            remote_display=self._remote_display,
            set_status=self.set_status,
            on_frequency_changed=self._on_frequency_changed,
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
