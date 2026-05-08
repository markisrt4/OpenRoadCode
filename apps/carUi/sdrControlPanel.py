import subprocess
import tkinter as tk
from dataclasses import dataclass
from typing import Callable, Dict, Optional
from pathlib import Path

from apps.carUi.aircraft_panel_manager import AircraftPanelManager
from apps.carUi.ham_radio_panel_manager import HamRadioPanelManager
from apps.carUi.weather_panel_manager import WeatherPanelManager
from apps.carUi.fm_radio_panel_manager import FMRadioPanelManager

from apps.carUi.radio_panel_manager import (
    RadioPanelManager,
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
        self.geometry("1024x600")
        self.minsize(800, 480)
        self.configure(bg=COLORS["app_bg"])
        self.attributes("-fullscreen", True)

        self.status_var = tk.StringVar(value="Ready")
        self.content_frame: Optional[tk.Frame] = None
        self.current_freq_var = tk.StringVar(value="Freq: --")
        self.location_var = tk.StringVar(value="🌎 lat.--, lon.--")

        self._build_ui()
        self.show_main_menu()
        self.bind("<Escape>", self._toggle_fullscreen)

        self.aircraft_panel_manager = AircraftPanelManager(self)
        self.fm_radio_panel_manager = FMRadioPanelManager(self)
        self.ham_radio_panel_manager = HamRadioPanelManager(self)
        self.weather_panel_manager = WeatherPanelManager(self)

    # ---------------------------
    # UI Construction
    # ---------------------------
    def _build_ui(self) -> None:
        container = tk.Frame(self, bg=COLORS["app_bg"])
        container.pack(fill="both", expand=True)

        self.top_bar = tk.Frame(container, bg=COLORS["top_bar_bg"], height=68)
        self.top_bar.pack(fill="x", side="top")
        self.top_bar.pack_propagate(False)

        self.top_bar.columnconfigure(0, weight=1)
        self.top_bar.columnconfigure(1, weight=1)
        self.top_bar.columnconfigure(2, weight=1)

        left_group = tk.Frame(self.top_bar, bg=COLORS["top_bar_bg"])
        left_group.grid(row=0, column=0, sticky="w", padx=(10, 0), pady=8)

        center_group = tk.Frame(self.top_bar, bg=COLORS["top_bar_bg"])
        center_group.grid(row=0, column=1, sticky="nsew", pady=8)

        right_group = tk.Frame(self.top_bar, bg=COLORS["top_bar_bg"])
        right_group.grid(row=0, column=2, sticky="e", padx=(0, 16), pady=8)

        self.left_button = tk.Button(
            left_group,
            text="",
            font=FONTS["back"],
            bg=COLORS["top_bar_bg"],
            fg=COLORS["top_bar_fg"],
            activebackground=COLORS["top_bar_active"],
            activeforeground=COLORS["top_bar_fg"],
            bd=1,
            padx=16,
            pady=6,
            cursor="hand2",
            command=self.show_main_menu,
        )
        self.left_button.pack(side="left", padx=(0, 12))
        self.left_button.pack_forget()

        self.title_label = tk.Label(
            left_group,
            text="Mark's CarSDR Control Panel",
            font=FONTS["title"],
            bg=COLORS["top_bar_bg"],
            fg=COLORS["top_bar_fg"],
        )
        self.title_label.pack(side="left")

        self.freq_label = tk.Label(
            center_group,
            textvariable=self.current_freq_var,
            font=("Arial", 18, "bold"),
            bg=COLORS["top_bar_bg"],
            fg=COLORS["top_bar_fg"],
            anchor="center",
        )
        self.freq_label.pack(expand=True)

        self.location_label = tk.Label(
            right_group,
            textvariable=self.location_var,
            font=FONTS["status"],
            bg=COLORS["top_bar_bg"],
            fg=COLORS["top_bar_fg"],
            padx=10,
        )
        self.location_label.pack(side="left", padx=(0, 12))

        self.power_button = tk.Button(
            right_group,
            text="⏻",
            font=("Arial", 18, "bold"),
            bg=COLORS["power_bg"],
            fg=COLORS["power_fg"],
            activebackground=COLORS["power_active"],
            activeforeground=COLORS["power_fg"],
            bd=0,
            width=4,
            height=1,
            command=self.power_off,
            cursor="hand2",
        )
        self.power_button.pack(side="right")

        self.content_frame = tk.Frame(container, bg=COLORS["app_bg"])
        self.content_frame.pack(fill="both", expand=True, padx=18, pady=18)

        status_bar = tk.Label(
            container,
            textvariable=self.status_var,
            anchor="w",
            bg=COLORS["status_bg"],
            fg=COLORS["status_fg"],
            font=FONTS["status"],
            padx=14,
            pady=10,
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
            ("ham_radio", "HAM RADIO", "Amateur bands", "Scanner / SDR", 1, 0),
            ("lighting", "LIGHTING", "Cabin / accent", "Controls", 1, 1),
            ("settings", "SETTINGS", "System", "Display / radio config", 1, 2),
        ]

        for key, title, subtitle, detail, row, col in tile_map:
            spec = TileSpec(key, title, "")
            tile = self._create_car_tile(dashboard, spec, subtitle, detail)
            tile.grid(row=row, column=col, sticky="nsew", padx=10, pady=10)

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
        tile = tk.Frame(
            parent,
            bg=COLORS["tile_bg"],
            highlightthickness=2,
            highlightbackground=COLORS["tile_border"],
            highlightcolor=COLORS["tile_accent"],
            bd=0,
            cursor="hand2",
        )

        accent = tk.Frame(tile, bg=COLORS["tile_accent"], height=5)
        accent.pack(fill="x", side="top")

        body = tk.Frame(tile, bg=COLORS["tile_bg"])
        body.pack(fill="both", expand=True, padx=22, pady=10)

        title = tk.Label(
            body,
            text=spec.label,
            font=FONTS["tile_title"],
            bg=COLORS["tile_bg"],
            fg=COLORS["tile_title"],
            anchor="w",
        )
        title.pack(fill="x", anchor="w")

        subtitle_label = tk.Label(
            body,
            text=subtitle,
            font=FONTS["tile_subtitle"],
            bg=COLORS["tile_bg"],
            fg=COLORS["tile_subtitle"],
            anchor="w",
        )

        subtitle_label.pack(fill="x", anchor="w", pady=(4, 0))

        detail_label = tk.Label(
            body,
            text=detail,
            font=FONTS["tile_detail"],
            bg=COLORS["tile_bg"],
            fg=COLORS["tile_detail"],
            anchor="w",
        )
        detail_label.pack(fill="x", anchor="w", pady=(8, 0))

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
        self.title_label.config(text="Mark's CarSDR Control Panel")
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
