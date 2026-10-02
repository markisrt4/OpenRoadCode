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
        if self._on_radar_toggle is not None:
            self._radar_button = tk.Button(
                bar,
                text="RADAR",
                command=self._toggle_radar,
                bg=ui.control_background,
                fg=ui.text,
                activebackground=ui.control_active,
                activeforeground="#ffffff",
                relief=tk.FLAT,
                highlightthickness=1,
                highlightbackground=ui.border,
                font=("Sans", FONT_CONTROL, "bold"),
                width=17,
                height=1,
                padx=3,
                pady=1,
            )
            self._radar_button.pack(side=tk.RIGHT, padx=(4, 0), pady=3)
            self._render_radar_state()

            for label, callback in (
                ("LIVE", self._on_radar_live),
                ("▶", self._on_radar_next),
                ("◀", self._on_radar_previous),
            ):
                if callback is not None:
                    tk.Button(
                        bar,
                        text=label,
                        command=callback,
                        bg=ui.control_background,
                        fg=ui.text,
                        activebackground=ui.control_active,
                        activeforeground="#ffffff",
                        relief=tk.FLAT,
                        highlightthickness=1,
                        highlightbackground=ui.border,
                        font=("Sans", FONT_CONTROL, "bold"),
                        padx=5,
                        pady=1,
                    ).pack(side=tk.RIGHT, padx=(4, 0), pady=3)

            self._classic_radar_var = tk.BooleanVar(
                value=self._radar_palette is RadarPalette.CLASSIC
            )
            tk.Checkbutton(
                bar,
                text="CLASSIC",
                variable=self._classic_radar_var,
                command=self._toggle_radar_palette,
                bg=ui.surface_alt,
                fg=ui.text,
                activebackground=ui.surface_alt,
                activeforeground=ui.text,
                selectcolor=ui.control_background,
                font=("Sans", FONT_CONTROL, "bold"),
                padx=3,
                pady=1,
            ).pack(side=tk.RIGHT, padx=(4, 0), pady=3)


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
        self._radar_button.configure(
            text=self._radar_button_text(),
            fg=ui.accent_success if self._radar_enabled else ui.text,
        )

    def _radar_button_text(self) -> str:
        if not self._radar_enabled:
            return "RADAR"
        if self._radar_frame_time is None:
            return "RADAR • …"

        from datetime import datetime

        frame = datetime.fromtimestamp(self._radar_frame_time).astimezone()
        return f"RADAR • {frame.strftime('%-I:%M %p')}"
