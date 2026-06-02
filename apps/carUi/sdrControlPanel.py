import tkinter as tk
import os
from dataclasses import dataclass
from turtle import title
from typing import Callable, Dict, Optional
from pathlib import Path

from apps.carUi.aircraft_panel_manager  import AircraftPanelManager
from apps.carUi.scanner_panel_manager   import ScannerPanelManager
from apps.carUi.weather_panel_manager   import WeatherPanelManager
from apps.carUi.fm_radio_panel_manager  import FMRadioPanelManager
from apps.carUi.settings_panel_manager  import SettingsPanelManager

from apps.common.uiTheme import COLORS, FONTS, FONT_FAMILY

from modules.audio.audio_controller import AudioController
from modules.audio.pipewire_audio_controller import PipewireAudioController

from apps.launchers.process_manager import close_display_apps

from apps.carUi.top_bar import CarTopBar
from apps.carUi.gps_ui_monitor import GPSUIMonitor

@dataclass(frozen=True)
class TileSpec:
    key: str
    label: str
    icon: str


class SDRControlPanel(tk.Tk):
    def __init__(
        self,
        callbacks: Optional[Dict[str, Callable[[str], None]]] = None,
        title: str = "SDR Control Panel",
        remote_display: str = ":2",
    ) -> None:
        super().__init__()

        self.callbacks: Dict[str, Callable[[str], None]] = callbacks or {}
        self.remote_display = remote_display

        self.title(title)

        ui_geometry = os.getenv("CARSDR_GEOMETRY", "1024x600")
        fullscreen  = os.getenv("CARSDR_FULLSCREEN", "1") == "1"

        self.compact_ui = self._geometry_is_compact(ui_geometry)

        self.geometry(ui_geometry)
        if self.compact_ui:
            self.minsize(800, 480)
            self.maxsize(800, 480)
        else:
            self.minsize(800, 480)

        self.attributes("-fullscreen", fullscreen)

        self.configure(bg=COLORS["app_bg"])

        self.status_var = tk.StringVar(value="Ready")
        self.content_frame: Optional[tk.Frame] = None

        self.audio_controller = AudioController(PipewireAudioController(steps=8))
        self.volume_level = self.audio_controller.get_volume_level()

        self.gps_ui_monitor = GPSUIMonitor(
            root=self,
            get_gps_device=lambda: getattr(self, "gps_device", None),
            set_location_text=lambda text: self.top_bar.set_location_text(text),
        )

        self._build_ui()
        self.show_main_menu()
        self.bind("<Escape>", self._toggle_fullscreen)

        self.aircraft_panel_manager = AircraftPanelManager(self)
        self.fm_radio_panel_manager = FMRadioPanelManager (self)
        self.scanner_panel_manager  = ScannerPanelManager (self)
        self.weather_panel_manager  = WeatherPanelManager (self)
        self.settings_panel_manager = SettingsPanelManager(self)


    @staticmethod
    def _geometry_is_compact(geometry: str) -> bool:
        """
        Decide compact UI from requested app geometry, not physical monitor size.

        Tk's winfo_screenwidth()/height() reports the host display, which is useless
        when testing an 800x480 Pi layout inside a window on a larger monitor.
        """
        try:
            size = geometry.split("+", 1)[0]
            width_text, height_text = size.lower().split("x", 1)
            width = int(width_text)
            height = int(height_text)
            return width <= 900 or height <= 520
        except Exception:
            return False

    # ---------------------------
    # UI Construction
    # ---------------------------
    def _build_ui(self) -> None:

        print(f"[UI] Loaded SDRControlPanel from: {__file__}")
        print(f"[UI] Screen size: {self.winfo_screenwidth()}x{self.winfo_screenheight()}")

        small_display = (
            self.winfo_screenwidth() <= 1024
            or self.winfo_screenheight() <= 600
        )
        print(f"[UI] small_display={small_display}")
        
        container = tk.Frame(self, bg=COLORS["app_bg"])
        container.pack(fill="both", expand=True)

        self.top_bar = CarTopBar(
            container,
            compact_ui=self.compact_ui,
            on_back=self.show_main_menu,
            on_volume_down=self.volume_down,
            on_volume_up=self.volume_up,
            on_power=self.power_off,
            volume_level=self.volume_level,
            volume_steps=8,
        )
        self.top_bar.pack(fill="x", side="top")

        self.content_frame = tk.Frame(container, bg=COLORS["app_bg"])
        self.content_frame.pack(fill="both", expand=True, padx=8 if small_display else 18, pady=8 if small_display else 18)

        status_bar = tk.Label(
            container,
            textvariable=self.status_var,
            anchor="w",
            bg=COLORS["status_bg"],
            fg=COLORS["status_fg"],
            font=(
                ("Arial", 9)
                if small_display
                else FONTS["status"]
            ),
            padx=10 if small_display else 14,
            pady=4 if small_display else 10,
        )
        status_bar.pack(fill="x", side="bottom")

    def _build_main_tile_grid(self) -> None:
        """
        Populate the main dashboard tiles.
        """
        if self.content_frame is None:
            return

        self._clear_content()

        dashboard = tk.Frame(self.content_frame, bg=COLORS["app_bg"])
        dashboard.pack(fill="both", expand=True)

        for col in range(3):
            dashboard.columnconfigure(col, weight=1, uniform="dash_col")
        for row in range(2):
            dashboard.rowconfigure(row, weight=1, uniform="dash_row")

        tile_map = [
            ("fm_radio",      "FM RADIO", "FM Broadcast radio", "Tune FM stations",           0, 0),
            ("weather",       "WEATHER",  "Forecast + WX band", "Radar / NOAA",               0, 1),
            ("aircraft",      "AIRCRAFT", "ADS-B + Airband",    "Traffic / chatter",          0, 2),
            ("scanner_radio", "SCANNER",  "Radio Monitoring",   "Police / Fire / HAM / GMRS", 1, 0),
            ("lighting",      "LIGHTING", "Cabin / accent",     "Lighting Controls",          1, 1),
            ("settings",      "SETTINGS", "System",             "Display / radio config",     1, 2),
        ]

        for key, title, subtitle, detail, row, col in tile_map:
            spec = TileSpec(key, title, "")
            tile = self._create_car_tile(dashboard, spec, subtitle, detail)
            tile.grid(row=row, column=col, sticky="nsew", padx=6 if self.compact_ui else 10, pady=6 if self.compact_ui else 10)

    def _toggle_fullscreen(self, event=None) -> None:
        current = bool(self.attributes("-fullscreen"))
        self.attributes("-fullscreen", not current)
        mode = "enabled" if not current else "disabled"
        self.status_var.set(f"Fullscreen {mode}")

    def _clear_tile_focus(self, widget: tk.Widget) -> None:
        """
        Optional: Reset visual focus effects on a tile when mouse released.
        Currently a no-op placeholder; extend if you add tile highlighting.
        """
        # Example: if you had a highlight effect, remove it here
        pass

    # ---------------------------
    # Tiles / Panels
    # ---------------------------
    def _clear_content(self) -> None:
        if self.content_frame is None:
            return
        for child in self.content_frame.winfo_children():
            child.destroy()

    def _create_car_tile(
        self,
        parent: tk.Widget,
        spec: TileSpec,
        subtitle: str,
        detail: str,
    ) -> tk.Frame:
        small = self.compact_ui
        is_main_tile = spec.key in {
            "fm_radio",
            "weather",
            "aircraft",
            "scanner_radio",
            "lighting",
            "settings",
        }

        is_preset = "_preset_" in spec.key and not is_main_tile
        
        if small:
            if is_main_tile:
                title_font = ("Arial", 19, "bold")
                subtitle_font = ("Arial", 10)
                detail_font = ("Arial", 9)
            elif is_preset:
                title_font = ("Arial", 18, "bold")
                subtitle_font = ("Arial", 9)
                detail_font = ("Arial", 8)
            else:
                title_font = ("Arial", 17, "bold")
                subtitle_font = ("Arial", 10)
                detail_font = ("Arial", 9)

            body_padx = 12
            body_pady = 8
            top_accent_height = 4

        else:
            title_font = FONTS["tile_title"]
            subtitle_font = FONTS["tile_subtitle"]
            detail_font = FONTS["tile_detail"]
            body_padx = 22
            body_pady = 18
            top_accent_height = 5

        tile = tk.Frame(
            parent,
            bg=COLORS["tile_bg"],
            highlightthickness=2,
            highlightbackground=COLORS["tile_border"],
            highlightcolor=COLORS["tile_accent"],
            bd=0,
            cursor="hand2",
        )

        accent = tk.Frame(tile, bg=COLORS["tile_accent"], height=top_accent_height)
        accent.pack(fill="x", side="top")

        body = tk.Frame(tile, bg=COLORS["tile_bg"])
        body.pack(fill="both", expand=True, padx=body_padx, pady=body_pady)

        title = tk.Label(
            body,
            text=spec.label,
            font=title_font,
            bg=COLORS["tile_bg"],
            fg=COLORS["tile_title"],
            anchor="center" if is_preset else "w",
            justify="center" if is_preset else "left",
            wraplength=180 if small else 260,
        )
        title.pack(fill="x", anchor="center" if is_preset else "w")

        subtitle_label = tk.Label(
            body,
            text=subtitle,
            font=subtitle_font,
            bg=COLORS["tile_bg"],
            fg=COLORS["tile_subtitle"],
            anchor="center" if is_preset else "w",
            justify="center" if is_preset else "left",
            wraplength=220 if small else 300,
        )
        subtitle_label.pack(
            fill="x",
            anchor="center" if is_preset else "w",
            pady=(3, 0),
        )

        detail_label = tk.Label(
            body,
            text=detail,
            font=detail_font,
            bg=COLORS["tile_bg"],
            fg=COLORS["tile_detail"],
            anchor="center" if is_preset else "w",
            justify="center" if is_preset else "left",
            wraplength=220 if small else 300,
        )
        detail_label.pack(
            fill="x",
            anchor="center" if is_preset else "w",
            pady=(2, 0),
        )

        self._bind_click_recursive(tile, spec)
        return tile

    def create_subpanel_tile(
        self,
        parent: tk.Widget,
        key: str,
        label: str,
        subtitle: str,
        detail: str,
    ) -> tk.Frame:
        spec = TileSpec(key, label, "")
        return self._create_car_tile(parent, spec, subtitle, detail)

    # ---------------------------
    # Callbacks / Events
    # ---------------------------
    def _bind_click_recursive(self, widget: tk.Widget, spec: TileSpec) -> None:
        widget.bind("<Button-1>", lambda event, s=spec: self._on_tile_clicked(s))
        widget.bind("<ButtonRelease-1>", lambda event, w=widget: self._clear_tile_focus(w))

        if isinstance(widget, (tk.Frame, tk.Label)):
            for child in widget.winfo_children():
                self._bind_click_recursive(child, spec)

    def _on_tile_clicked(self, spec: TileSpec) -> None:
        self.status_var.set(f"Selected: {spec.label}")
        self._run_callback(spec.key)

    def _run_callback(self, key: str) -> None:
        callback = self.callbacks.get(key)
        if callback is None:
            return
        try:
            callback(key)
        except Exception as exc:
            self.status_var.set(f"Callback error in {key}: {exc}")
            print(f"[UI] Callback error for {key}: {exc}")

    # ---------------------------
    # Panel navigation
    # ---------------------------
    def show_main_menu(self) -> None:
        title_text = (
            "CarSDR"
            if self.compact_ui
            else "Mark's CarSDR Control Panel"
        )

        self.top_bar.set_title(title_text)
        self.top_bar.set_back_command(self.show_main_menu)
        self.top_bar.hide_back_button()
        self._build_main_tile_grid()
        self.status_var.set("Ready")

    def show_aircraft_menu(self) -> None:
        self.aircraft_panel_manager.show()

    def show_scanner_radio_menu(self) -> None:
        self.scanner_panel_manager.show()

    def show_fm_radio_menu(self) -> None:
        self.fm_radio_panel_manager.show()

    def show_settings_menu(self) -> None:
        self.settings_panel_manager.show()

    def volume_up(self) -> None:
        self.volume_level = self.audio_controller.volume_up()
        self.top_bar.set_volume_level(self.volume_level)
        self.status_var.set("Volume up")

    def volume_down(self) -> None:
        self.volume_level = self.audio_controller.volume_down()
        self.top_bar.set_volume_level(self.volume_level)
        self.status_var.set("Volume down")

    def _adjust_system_volume(self, amount: str) -> None:
        try:
            subprocess.run(
                ["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", amount],
                check=False,
            )
            self.status_var.set(f"Volume {amount}")
        except Exception as exc:
            self.status_var.set(f"Volume control failed: {exc}")
            print(f"[UI] Volume control failed: {exc}")

    def power_off(self) -> None:
        """
        Shut down CarSDR: close all remote display apps on :2 and quit the Tk app.
        Does NOT affect the host X session.
        """
        try:
            self.status_var.set("Shutting down CarSDR apps...")

            # Close only apps on the remote display
            from apps.launchers.process_manager import close_display_apps
            close_display_apps(display=self.remote_display)

        except Exception as exc:
            print(f"[UI] power_off error: {exc}")

        # Quit the Tk main loop and destroy the window
        self.quit()    # exits mainloop
        self.destroy() # destroys Tk root window

    def show_weather_menu(self) -> None:
        self.weather_panel_manager.show()

    def set_current_frequency(self, frequency_hz: int | None) -> None:
        if frequency_hz is None:
            self.top_bar.set_frequency_text("--")
            return

        self.top_bar.set_frequency_text(self._format_frequency(frequency_hz))

    def set_location(self, lat: float | None, lon: float | None) -> None:
        if lat is None or lon is None:
            self.top_bar.set_location_text("🌎 lat.--, lon.--")
            return

        self.top_bar.set_location_text(f"🌎 lat.{lat:.4f}, lon.{lon:.4f}")

    def start_gps_ui_updates(self, interval_ms: int = 1000) -> None:
        self.gps_ui_monitor.start(interval_ms)

    def stop_gps_ui_updates(self) -> None:
        self.gps_ui_monitor.stop()

    def set_panel_title(self, title: str) -> None:
        self.top_bar.set_title(title)


    @staticmethod
    def _format_frequency(frequency_hz: int) -> str:
        if frequency_hz >= 1_000_000:
            value = f"{frequency_hz / 1_000_000:.3f}".rstrip("0").rstrip(".")
            return f"{value} MHz"

        if frequency_hz >= 1_000:
            value = f"{frequency_hz / 1_000:.3f}".rstrip("0").rstrip(".")
            return f"{value} kHz"

        return f"{frequency_hz} Hz"
