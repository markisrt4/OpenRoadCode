# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Weather-radar controls shared with the navigation panel."""

import tkinter as tk

from controllers.weather.radar_palette import RadarPalette
from .shell_metrics import FONT_CONTROL

_RADAR_OVERVIEW_ZOOM = 7.5


class NavigationRadarControls:
    """Build radar widgets and handle frame, palette, and visibility controls."""

    def _build_radar_controls(self, bar: tk.Frame) -> None:
        ui = self._theme_bundle.ui
        self._radar_button = None
        if self._on_radar_toggle is None:
            return
        self._radar_button = tk.Menubutton(
            bar, text="☰ RADAR", bg=ui.control_background, fg=ui.text,
            activebackground=ui.control_active, activeforeground=ui.control_text,
            relief=tk.FLAT, font=("Sans", FONT_CONTROL, "bold"), padx=8, pady=4,
        )
        menu = tk.Menu(self._radar_button, tearoff=False,
                       bg=ui.control_background, fg=ui.control_text,
                       activebackground=ui.control_active, activeforeground=ui.control_text)
        self._radar_menu = menu
        self._radar_visible_var = tk.BooleanVar(value=self._radar_enabled)
        menu.add_checkbutton(label="Show weather radar", variable=self._radar_visible_var,
                             command=self._toggle_radar)
        menu.add_separator()
        for label, callback in (
            ("Previous frame", self._on_radar_previous),
            ("Next frame", self._on_radar_next),
            ("Latest / live", self._on_radar_live),
        ):
            if callback is not None:
                menu.add_command(label=label, command=callback)
        menu.add_separator()
        self._classic_radar_var = tk.BooleanVar(value=self._radar_palette is RadarPalette.CLASSIC)
        menu.add_checkbutton(label="Classic palette", variable=self._classic_radar_var,
                             command=self._toggle_radar_palette)
        self._radar_button.configure(menu=menu)
        self._radar_button.pack(side=tk.RIGHT, padx=(4, 0), pady=3)
        self._render_radar_state()

    def _toggle_radar(self) -> None:
        self._radar_enabled = not self._radar_enabled
        if self._radar_enabled:
            self._pre_radar_zoom = self._zoom_level
            self._zoom_level = _RADAR_OVERVIEW_ZOOM
            self._request_handler.request_zoom(self._zoom_level)
        elif self._pre_radar_zoom is not None:
            self._zoom_level = self._pre_radar_zoom
            self._pre_radar_zoom = None
            self._request_handler.request_zoom(self._zoom_level)
        self._render_radar_state()
        if self._on_radar_toggle is not None:
            self._on_radar_toggle(self._radar_enabled)

    def _toggle_radar_palette(self) -> None:
        self._radar_palette = (
            RadarPalette.CLASSIC if self._classic_radar_var.get()
            else RadarPalette.UNIVERSAL
        )
        if self._on_radar_palette_changed is not None:
            self._on_radar_palette_changed(self._radar_palette)

    def set_radar_frame_time(self, frame_time: int | None) -> None:
        """Show the timestamp of the radar frame currently on the map."""
        self._radar_frame_time = frame_time
        self._render_radar_state()

    def _render_radar_state(self) -> None:
        if self._radar_button is None:
            return
        ui = self._theme_bundle.ui
        if hasattr(self, "_radar_visible_var"):
            self._radar_visible_var.set(self._radar_enabled)
        self._radar_button.configure(
            text="☰ RADAR ●" if self._radar_enabled else "☰ RADAR",
            fg=ui.accent_success if self._radar_enabled else ui.text,
        )

        if hasattr(self, "_radar_menu"):
            self._radar_menu.entryconfigure(0, label="Show weather radar" if not self._radar_enabled
                                            else self._radar_button_text())
            for index in range(2, self._radar_menu.index("end") - 1):
                self._radar_menu.entryconfigure(index, state=tk.NORMAL if self._radar_enabled
                                                else tk.DISABLED)

    def _radar_button_text(self) -> str:
        if not self._radar_enabled:
            return "RADAR"
        if self._radar_frame_time is None:
            return "RADAR • …"

        from datetime import datetime

        frame = datetime.fromtimestamp(self._radar_frame_time).astimezone()
        return f"RADAR • {frame.strftime('%-I:%M %p')}"
