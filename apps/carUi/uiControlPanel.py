from __future__ import annotations

import os
import tkinter as tk
from collections.abc import Sequence
from typing import Callable, Dict, Optional

from apps.carUi.gps_ui_monitor import GPSUIMonitor
from apps.carUi.input import EncoderEventRouter, PanelEncoderCallbacks
from apps.carUi.panels.aircraft_panel_manager import AircraftPanelManager
from apps.carUi.panels.fm_radio_panel_manager import FMRadioPanelManager
from apps.carUi.panels.lighting_panel_manager import LightingPanelManager
from apps.carUi.panels.scanner_panel_manager import ScannerPanelManager
from apps.carUi.panels.spotify_panel_manager import SpotifyPanelManager
from apps.carUi.panels.weather_panel_manager import WeatherPanelManager
from apps.carUi.navigation import (
    MenuPage,
    MenuRenderer,
    MenuTile,
    NavigationController,
    PanelRouter,
)
from apps.carUi.runtime.radio_runtime import CarUiRuntime
from apps.carUi.system import (
    SystemControlManager,
    SystemController,
    VehicleStatusManager,
    VolumeManager,
)
from apps.carUi.panels.status_bar_panel import StatusBarPanel
from apps.carUi.panels.top_bar_panel import TopBarPanel
from apps.common.uiTheme.uiTheme import (
    CAR_UI_THEME,
    STATUS_BAR_THEME,
    TOP_BAR_THEME,
)
from controllers.audio.audio_controller_if import AudioControllerIf
from hardware_io.gps.gps_reader import GpsReader
from hardware_io.rotary_encoder import RotaryEncoderIf
from controllers.spotify import SpotifyControllerIf
from controllers.lighting.lighting_controller_if import LightingControllerIf

class UiControlPanel(tk.Tk):
    """Top-level Car UI window coordinating panels and hardware input."""
    def __init__(
        self,
        runtime: CarUiRuntime,
        gps_device: GpsReader,
        lighting_controller: LightingControllerIf,
        audio_controller: AudioControllerIf,
        spotify_controller: SpotifyControllerIf,
        rotary_encoders: Sequence[RotaryEncoderIf],
        volume_encoder_index: int,
        callbacks: Optional[Dict[str, Callable[[str], None]]] = None,
        title: str = "Ui Control Panel",
    ) -> None:
        super().__init__()

        self.runtime = runtime
        self.gps_device = gps_device
        self.lighting_controller = lighting_controller
        self.audio_controller = audio_controller
        self.spotify_controller = spotify_controller
        self.remote_display = runtime.remote_display
        self.callbacks: Dict[str, Callable[[str], None]] = callbacks or {}

        self.title(title)

        self.theme = CAR_UI_THEME
        self.colors = self.theme["colors"]
        self.layout = self.theme["layout"]

        ui_geometry = self._get_ui_geometry()
        fullscreen = (
            os.getenv(self.theme["window"]["fullscreen_env"], "0") == "1"
        )
        self.compact_ui = self._geometry_is_compact(ui_geometry)
        self.style = self.theme["profiles"][
            "compact" if self.compact_ui else "normal"
        ]

        self.geometry(ui_geometry)
        self.minsize(*self.theme["window"]["minimum_size"])
        self.attributes("-fullscreen", fullscreen)
        self.configure(bg=self.colors["app_bg"])

        self.content_frame: Optional[tk.Frame] = None

        self.system_controller = SystemController(
            remote_display=self.remote_display,
        )
        self.volume_level = self._initial_volume_level()
        self.volume_muted = self._initial_volume_muted()

        self._build_ui()

        self.vehicle_status_manager = VehicleStatusManager(
            set_frequency_text=self.top_bar.set_frequency_text,
            set_location_text=self.top_bar.set_location_text,
            empty_value=self.layout["empty_value"],
        )

        self.gps_ui_monitor = GPSUIMonitor(
            root=self,
            gps_reader=self.gps_device,
            set_position=self.vehicle_status_manager.set_location,
            set_status=self.status_bar.set_status,
        )
        self.navigation = NavigationController(
            content_frame=self.content_frame,
            top_bar=self.top_bar,
            set_status=self.status_bar.set_status,
        )
        self.menu_renderer = MenuRenderer(
            content_frame=self.content_frame,
            colors=self.colors,
            layout=self.layout,
            style=self.style,
            on_tile_clicked=self._run_callback,
        )
        self.show_main_menu()
        self.bind("<Escape>", self._toggle_fullscreen)

        self.aircraft_panel_manager = AircraftPanelManager(self)
        self.fm_radio_panel_manager = FMRadioPanelManager(self)
        self.scanner_panel_manager = ScannerPanelManager(self)
        self.weather_panel_manager = WeatherPanelManager(self)
        # self.settings_panel_manager = SettingsPanelManager(self)
        self.lighting_panel_manager = LightingPanelManager(self)
        self.spotify_panel_manager = SpotifyPanelManager(
            self,
            spotify_controller=self.spotify_controller,
        )

        self.volume_manager = VolumeManager(
            audio_controller=self.audio_controller,
            indicator_steps=self.layout["volume_steps"],
            set_volume_level=self.top_bar.set_volume_level,
            set_muted=self.top_bar.set_volume_muted,
            set_status=self.status_bar.set_status,
        )
        self.encoder_event_router = EncoderEventRouter(
            root=self,
            encoders=rotary_encoders,
            volume_encoder_index=volume_encoder_index,
            volume_up=self.volume_manager.volume_up,
            volume_down=self.volume_manager.volume_down,
            volume_button_pressed=self.volume_manager.toggle_mute,
        )

        self.system_control_manager = SystemControlManager(
            system_controller=self.system_controller,
            set_status=self.status_bar.set_status,
            request_close=self._close_window,
        )

        self.panel_router = PanelRouter()
        self._register_panel_routes()
        self.protocol("WM_DELETE_WINDOW", self._close_window)

    def register_default_callbacks(self) -> None:
        self.callbacks.clear()
        self.callbacks.update(
            {
                key: lambda _selected_key, route_key=key: self.panel_router.open(
                    route_key
                )
                for key in self.panel_router.keys()
            }
        )

    def _register_panel_routes(self) -> None:
        self.panel_router.register_many(
            {
                "radio": lambda: self.show_menu("radio"),
                "aircraft": self.aircraft_panel_manager.show,
                "gauges": lambda: self.show_menu("gauges"),
                "weather": self.weather_panel_manager.show,
                "lighting": self.lighting_panel_manager.show,
                "media": lambda: self.show_menu("media"),
                "fm_radio": self.fm_radio_panel_manager.show,
                "scanner_radio": self.scanner_panel_manager.show,
                "spotify": self.spotify_panel_manager.show,
            }
        )

    def _get_ui_geometry(self) -> str:
        window_theme = self.theme["window"]
        explicit_geometry = os.getenv(window_theme["geometry_env"])
        if explicit_geometry:
            return explicit_geometry

        profile = os.getenv(
            window_theme["profile_env"],
            window_theme["default_profile"],
        ).strip().lower()
        return window_theme["profiles"].get(
            profile,
            window_theme["default_geometry"],
        )

    def _geometry_is_compact(self, geometry: str) -> bool:
        try:
            size = geometry.split("+", 1)[0]
            width_text, height_text = size.lower().split("x", 1)
            width = int(width_text)
            height = int(height_text)
            window_theme = self.theme["window"]
            return (
                width <= window_theme["compact_max_width"]
                or height <= window_theme["compact_max_height"]
            )
        except Exception:
            return False

    def _initial_volume_level(self) -> int:
        try:
            return VolumeManager.indicator_level(
                self.audio_controller.get_volume_level(),
                maximum_level=self.audio_controller.maximum_level,
                indicator_steps=self.layout["volume_steps"],
            )
        except Exception as exc:
            print(f"[UI] Unable to read initial volume: {exc}")
            return 0

    def _initial_volume_muted(self) -> bool:
        try:
            return self.audio_controller.is_muted()
        except Exception as exc:
            print(f"[UI] Unable to read initial mute state: {exc}")
            return False

    def _build_ui(self) -> None:
        print(f"[UI] Loaded UiControlPanel from: {__file__}")
        print(
            f"[UI] Screen size: "
            f"{self.winfo_screenwidth()}x{self.winfo_screenheight()}"
        )
        print(f"[UI] compact_ui={self.compact_ui}")

        container = tk.Frame(self, bg=self.colors["app_bg"])
        container.pack(fill=self.layout["fill_both"], expand=True)

        self.top_bar = TopBarPanel(
            container,
            compact_ui=self.compact_ui,
            theme=TOP_BAR_THEME,
            on_back=self.show_main_menu,
            on_volume_down=self._handle_volume_down,
            on_volume_up=self._handle_volume_up,
            on_settings=self._handle_settings,
            on_power=self._handle_power_off,
            volume_level=self.volume_level,
            volume_steps=self.layout["volume_steps"],
            volume_muted=self.volume_muted,
        )
        self.top_bar.pack(fill=self.layout["fill_horizontal"], side=self.layout["side_top"])

        self.content_frame = tk.Frame(container, bg=self.colors["app_bg"])
        self.content_frame.pack(
            fill="both",
            expand=True,
            padx=self.style["content_padx"],
            pady=self.style["content_pady"],
        )

        self.status_bar = StatusBarPanel(
            container,
            theme=STATUS_BAR_THEME,
            compact_ui=self.compact_ui,
            initial_status="Ready",
        )
        self.status_bar.pack(
            fill=self.layout["fill_horizontal"],
            side=self.layout["side_bottom"],
        )

    @staticmethod
    def _menu_pages() -> dict[str, MenuPage]:
        return {
            "main": MenuPage(
                title="OpenRoadCode",
                tiles=(
                    MenuTile("radio", "RADIO", "FM / Scanner / NOAA", "Broadcast and monitoring"),
                    MenuTile("aircraft", "AIRCRAFT", "ADS-B + Airband", "Traffic and chatter"),
                    MenuTile("gauges", "GAUGES", "OBD-II / telemetry", "Vehicle dashboard"),
                    MenuTile("weather", "WEATHER", "Forecast + alerts", "Conditions and warnings"),
                    MenuTile("lighting", "LIGHTING", "Cabin / accent", "Lighting controls"),
                    MenuTile("media", "MEDIA", "Spotify / audio", "Music and playback"),
                ),
                columns=3,
            ),
            "radio": MenuPage(
                title="Radio",
                tiles=(
                    MenuTile("fm_radio", "FM RADIO", "FM Broadcast radio", "Tune FM stations"),
                    MenuTile("scanner_radio", "SCANNER", "Radio monitoring", "Police / Fire / HAM / GMRS"),
                    MenuTile("weather", "NOAA WX", "Weather radio", "NOAA and alerts"),
                ),
                columns=3,
            ),
            "media": MenuPage(
                title="Media",
                tiles=(
                    MenuTile("spotify", "SPOTIFY", "Streaming control", "Spotify app integration"),
                ),
                columns=3,
            ),
            "gauges": MenuPage(
                title="Gauges",
                tiles=(
                    MenuTile(
                        "gauges_placeholder",
                        "COMING SOON",
                        "OBD-II gauges",
                        "RPM / boost / temps / voltage",
                    ),
                ),
                columns=3,
            ),
        }

    def _show_menu_page(self, menu_key: str) -> None:
        page = self._menu_pages().get(
            menu_key,
            self._menu_pages()["main"],
        )
        self.menu_renderer.show_page(page)

    def _build_main_tile_grid(self) -> None:
        self._show_menu_page("main")

    def _toggle_fullscreen(self, event=None) -> None:
        current = bool(self.attributes("-fullscreen"))
        self.attributes("-fullscreen", not current)
        mode = "enabled" if not current else "disabled"
        self.status_bar.set_status(f"Fullscreen {mode}")

    def create_subpanel_tile(
        self,
        parent: tk.Widget,
        key: str,
        label: str,
        subtitle: str,
        detail: str,
    ) -> tk.Frame:
        return self.menu_renderer.create_tile(
            parent=parent,
            tile=MenuTile(
                key=key,
                title=label,
                subtitle=subtitle,
                detail=detail,
            ),
        )

    def _run_callback(self, key: str) -> None:
        callback = self.callbacks.get(key)

        try:
            if callback is not None:
                callback(key)
            else:
                self.panel_router.open(key)
        except Exception as exc:
            self.status_bar.set_status(f"Navigation error in {key}: {exc}")
            print(f"[UI] Navigation error for {key}: {exc}")

    def show_main_menu(self) -> None:
        self.clear_panel_encoder_callbacks()
        title_text = (
            "OpenRoadCode"
            if self.compact_ui
            else "OpenRoadCode Control Panel"
        )
        self.navigation.show_root(
            title=title_text,
            builder=self._build_main_tile_grid,
            status="Ready",
            root_target=self.show_main_menu,
        )

    def show_menu(self, menu_key: str) -> None:
        self.clear_panel_encoder_callbacks()
        titles = {
            "radio": "Radio",
            "media": "Media",
            "gauges": "Gauges",
        }
        title = titles.get(menu_key, "OpenRoadCode")
        self.navigation.show_screen(
            title=title,
            builder=lambda: self._show_menu_page(menu_key),
            status=titles.get(menu_key, menu_key.title()),
            back_target=self.show_main_menu,
        )

    def _handle_volume_up(self) -> None:
        manager = getattr(self, "volume_manager", None)
        if manager is not None:
            manager.volume_up()

    def _handle_volume_down(self) -> None:
        manager = getattr(self, "volume_manager", None)
        if manager is not None:
            manager.volume_down()

    def _handle_power_off(self) -> None:
        manager = getattr(self, "system_control_manager", None)
        if manager is not None:
            manager.power_off()

    def _handle_settings(self) -> None:
        if self.panel_router.contains("settings"):
            self.panel_router.open("settings")
            return

        self.status_bar.set_status("Settings panel is not available")

    def set_panel_encoder_callbacks(
        self,
        callbacks: PanelEncoderCallbacks,
    ) -> None:
        self.encoder_event_router.set_panel_callbacks(callbacks)

    def clear_panel_encoder_callbacks(self) -> None:
        router = getattr(self, "encoder_event_router", None)
        if router is not None:
            router.clear_panel_callbacks()

    def start_encoder_events(self) -> None:
        self.encoder_event_router.start()

    def stop_encoder_events(self) -> None:
        self.encoder_event_router.stop()

    def _close_window(self) -> None:
        self.stop_encoder_events()
        self.gps_ui_monitor.stop()
        self.quit()
        self.destroy()

    def start_gps_ui_updates(self) -> None:
        self.gps_ui_monitor.start()

    def stop_gps_ui_updates(self) -> None:
        self.gps_ui_monitor.stop()
