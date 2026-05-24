import subprocess
import tkinter as tk
import os
from dataclasses import dataclass
from typing import Callable, Dict, Optional
from pathlib import Path

from apps.carUi.aircraft_panel_manager  import AircraftPanelManager
from apps.carUi.ham_radio_panel_manager import HamRadioPanelManager
from apps.carUi.weather_panel_manager   import WeatherPanelManager
from apps.carUi.fm_radio_panel_manager  import FMRadioPanelManager

from apps.carUi.radio.radio_panel_manager import (
    RadioPanelManager,
)

from apps.carUi.radio.radio_panel_config import (
    RadioPanelConfig,
    RadioPanelTileConfig,
)

from .uiTheme import COLORS, FONTS  # <- theme integrated

from apps.launchers.process_manager import close_display_apps

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
        self.current_freq_var = tk.StringVar(value="Freq: --")
        self.location_var = tk.StringVar(value="🌎 lat.--, lon.--")

        self._build_ui()
        self.show_main_menu()
        self.bind("<Escape>", self._toggle_fullscreen)

        self.aircraft_panel_manager  = AircraftPanelManager(self)
        self.fm_radio_panel_manager  = FMRadioPanelManager (self)
        self.ham_radio_panel_manager = HamRadioPanelManager(self)
        self.weather_panel_manager   = WeatherPanelManager (self)

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

        top_bar_height = 50 if small_display else 68

        self.top_bar = tk.Frame(
            container,
            bg=COLORS["top_bar_bg"],
            height=top_bar_height,
        )
        self.top_bar.pack(fill="x", side="top")
        self.top_bar.pack_propagate(False)

        self.top_bar.columnconfigure(0, weight=1)
        self.top_bar.columnconfigure(1, weight=1)
        self.top_bar.columnconfigure(2, weight=1)

        left_group = tk.Frame(self.top_bar, bg=COLORS["top_bar_bg"])
        left_group.grid(row=0, column=0, sticky="w", padx=(8, 0), pady=6 if small_display else 8)

        center_group = tk.Frame(self.top_bar, bg=COLORS["top_bar_bg"])
        center_group.grid(row=0, column=1, sticky="nsew", pady=6 if small_display else 8)

        right_group = tk.Frame(self.top_bar, bg=COLORS["top_bar_bg"])
        right_group.grid(row=0, column=2, sticky="e", padx=(0, 10 if small_display else 16), pady=6 if small_display else 8)

        self.left_button = tk.Button(
            left_group,
            text="",
            font=(("Arial", 12, "bold") if small_display else FONTS["back"]),
            bg=COLORS["top_bar_bg"],
            fg=COLORS["top_bar_fg"],
            activebackground=COLORS["top_bar_active"],
            activeforeground=COLORS["top_bar_fg"],
            bd=1,
            padx=10 if small_display else 16,
            pady=4 if small_display else 6,
            cursor="hand2",
            command=self.show_main_menu,
        )
        self.left_button.pack(side="left", padx=(0, 8 if small_display else 12))
        self.left_button.pack_forget()

        self.title_label = tk.Label(
            left_group,
            text=(
                "Mark's CarSDR"
                if small_display
                else "Mark's CarSDR Control Panel"
            ),
            font=(
                ("Arial", 16, "bold")
                if small_display
                else FONTS["title"]
            ),
            bg=COLORS["top_bar_bg"],
            fg=COLORS["top_bar_fg"],
        )
        self.title_label.pack(side="left")

        self.freq_label = tk.Label(
            center_group,
            textvariable=self.current_freq_var,
            font=(("Arial", 13, "bold") if small_display else ("Arial", 18, "bold")),
            bg=COLORS["top_bar_bg"],
            fg=COLORS["top_bar_fg"],
            anchor="center",
        )
        self.freq_label.pack(expand=True)

        self.location_label = tk.Label(
            right_group,
            textvariable=self.location_var,
            font=(("Arial", 9) if small_display else FONTS["status"]),
            bg=COLORS["top_bar_bg"],
            fg=COLORS["top_bar_fg"],
            padx=6 if small_display else 10,
        )
        self.location_label.pack(side="left", padx=(0, 8 if small_display else 12))

        self.power_button = tk.Button(
            right_group,
            text="⏻",
            font=(
                ("Arial", 14, "bold")
                if small_display
                else ("Arial", 18, "bold")
            ),
            width=3 if small_display else 4,
            height=1,
            bg=COLORS["power_bg"],
            fg=COLORS["power_fg"],
            activebackground=COLORS["power_active"],
            activeforeground=COLORS["power_fg"],
            bd=0,
            command=self.power_off,
            cursor="hand2",
        )
        self.power_button.pack(side="right")

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
            ("fm_radio", "FM RADIO", "Broadcast radio", "Launch SDR++ / presets", 0, 0),
            ("weather", "WEATHER", "Forecast + WX band", "Radar / NOAA", 0, 1),
            ("aircraft", "AIRCRAFT", "ADS-B + Airband", "Traffic / chatter", 0, 2),
            ("ham_radio", "HAM", "Amateur radio", "VHF / UHF", 1, 0),
            ("lighting", "LIGHTING", "Cabin / accent", "Controls", 1, 1),
            ("settings", "SETTINGS", "System", "Display / radio config", 1, 2),
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
            "ham_radio",
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

        self.title_label.config(text=title_text)
        self.left_button.pack_forget()
        self._build_main_tile_grid()
        self.status_var.set("Ready")

    def show_aircraft_menu(self) -> None:
        self.aircraft_panel_manager.show()

    def show_ham_radio_menu(self) -> None:
        self.ham_radio_panel_manager.show()

    def show_fm_radio_menu(self) -> None:
        self.fm_radio_panel_manager.show()

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
            self.current_freq_var.set("Freq: --")
            return

        self.current_freq_var.set(f"Freq: {self._format_frequency(frequency_hz)}")


    def set_location(self, lat: float | None, lon: float | None) -> None:
        if lat is None or lon is None:
            self.location_var.set("🌎 lat.--, lon.--")
            return

        self.location_var.set(f"🌎 lat.{lat:.4f}, lon.{lon:.4f}")


    @staticmethod
    def _format_frequency(frequency_hz: int) -> str:
        if frequency_hz >= 1_000_000:
            value = f"{frequency_hz / 1_000_000:.3f}".rstrip("0").rstrip(".")
            return f"{value} MHz"

        if frequency_hz >= 1_000:
            value = f"{frequency_hz / 1_000:.3f}".rstrip("0").rstrip(".")
            return f"{value} kHz"

        return f"{frequency_hz} Hz"
