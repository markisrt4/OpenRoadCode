# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Full off-road navigation and attitude panel for orcUi."""

from __future__ import annotations

import math
import tkinter as tk
from collections.abc import Callable

from apps.orcUi.navigation_presenter import AttitudePresentationState, PositionPresentationState
from apps.orcUi.theme_runtime import theme_bundle
from ui.theme import ThemeMode, UiTheme


class OffRoadPanel(tk.Frame):
    """Large off-road instrument panel driven only by presentation state."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        on_back: Callable[[], None],
        position: PositionPresentationState | None = None,
        attitude: AttitudePresentationState | None = None,
        show_header: bool = True,
        theme: UiTheme | None = None,
    ) -> None:
        self._theme = theme or theme_bundle(ThemeMode.DARK).ui
        super().__init__(parent, bg=self._theme.background)
        self._position = position or PositionPresentationState()
        self._attitude = attitude or AttitudePresentationState()
        self._heading_canvas: tk.Canvas
        self._attitude_canvas: tk.Canvas
        self._heading_label: tk.Label
        self._pitch_label: tk.Label
        self._roll_label: tk.Label
        self._position_labels: dict[str, tk.Label] = {}

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        content_row = 1 if show_header else 0
        self.grid_rowconfigure(content_row, weight=1)

        if show_header:
            header = tk.Frame(self, bg=self._theme.background)
            header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 6))
            tk.Button(
                header,
                text="‹ HOME",
                command=on_back,
                bg=self._theme.control_background,
                fg=self._theme.control_text,
                activebackground=self._theme.control_active,
                activeforeground="#ffffff",
                relief=tk.FLAT,
                bd=0,
                font=("Sans", 10, "bold"),
                padx=14,
                pady=6,
            ).pack(side=tk.LEFT)
            tk.Label(
                header,
                text="OFF-ROAD",
                fg=self._theme.accent_warning,
                bg=self._theme.background,
                font=("Sans", 13, "bold"),
            ).pack(side=tk.LEFT, padx=14)
            tk.Label(
                header,
                text="NAVIGATION + ATTITUDE",
                fg=self._theme.text_muted,
                bg=self._theme.background,
                font=("Monospace", 9),
            ).pack(side=tk.RIGHT, padx=4)

        instruments = tk.Frame(self, bg=self._theme.background)
        instruments.grid(row=content_row, column=0, sticky="nsew", padx=(0, 5))
        instruments.grid_rowconfigure(0, weight=1)
        instruments.grid_rowconfigure(1, weight=1)
        instruments.grid_columnconfigure(0, weight=1)

        compass = self._card(instruments)
        compass.grid(row=0, column=0, sticky="nsew", pady=(0, 5))
        tk.Label(
            compass,
            text="HEADING",
            fg=self._theme.accent_warning,
            bg=self._theme.surface,
            font=("Sans", 9, "bold"),
        ).pack(pady=(8, 0))
        self._heading_canvas = tk.Canvas(
            compass,
            width=210,
            height=120,
            bg=self._theme.surface,
            highlightthickness=0,
        )
        self._heading_canvas.pack(expand=True)
        self._heading_label = tk.Label(
            compass,
            text="--°",
            fg=self._theme.text,
            bg=self._theme.surface,
            font=("Sans", 18, "bold"),
        )
        self._heading_label.pack(pady=(0, 7))

        attitude_card = self._card(instruments)
        attitude_card.grid(row=1, column=0, sticky="nsew", pady=(5, 0))
        tk.Label(
            attitude_card,
            text="ATTITUDE",
            fg=self._theme.accent_primary,
            bg=self._theme.surface,
            font=("Sans", 9, "bold"),
        ).pack(pady=(8, 0))
        self._attitude_canvas = tk.Canvas(
            attitude_card,
            width=250,
            height=100,
            bg=self._theme.surface,
            highlightthickness=0,
        )
        self._attitude_canvas.pack(expand=True)
        values = tk.Frame(attitude_card, bg=self._theme.surface)
        values.pack(pady=(0, 7))
        self._pitch_label = tk.Label(
            values,
            text="PITCH --°",
            fg=self._theme.text,
            bg=self._theme.surface,
            font=("Sans", 11, "bold"),
        )
        self._pitch_label.pack(side=tk.LEFT, padx=14)
        self._roll_label = tk.Label(
            values,
            text="ROLL --°",
            fg=self._theme.text,
            bg=self._theme.surface,
            font=("Sans", 11, "bold"),
        )
        self._roll_label.pack(side=tk.LEFT, padx=14)

        position_card = self._card(self)
        position_card.grid(row=content_row, column=1, sticky="nsew", padx=(5, 0))
        tk.Label(
            position_card,
            text="POSITION",
            fg=self._theme.accent_success,
            bg=self._theme.surface,
            font=("Sans", 10, "bold"),
        ).pack(anchor="w", padx=16, pady=(14, 8))
        grid = tk.Frame(position_card, bg=self._theme.surface)
        grid.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 12))
        grid.grid_columnconfigure(1, weight=1)
        for row, (key, label, unit) in enumerate(
            (
                ("latitude", "Latitude", "°"),
                ("longitude", "Longitude", "°"),
                ("altitude", "Altitude", "ft"),
                ("fix", "GPS fix", ""),
                ("satellites", "Satellites", "used"),
                ("accuracy", "Accuracy", "m"),
            )
        ):
            tk.Label(
                grid,
                text=label,
                fg=self._theme.text_muted,
                bg=self._theme.surface,
                font=("Sans", 10),
            ).grid(row=row, column=0, sticky="w", pady=8)
            value = tk.Label(
                grid,
                text="--",
                fg=self._theme.text,
                bg=self._theme.surface,
                font=("Sans", 15, "bold"),
            )
            value.grid(row=row, column=1, sticky="e", padx=8, pady=8)
            tk.Label(
                grid,
                text=unit,
                fg=self._theme.text_muted,
                bg=self._theme.surface,
                font=("Monospace", 8),
            ).grid(row=row, column=2, sticky="w", pady=8)
            self._position_labels[key] = value

        self.update_position(self._position)
        self.update_attitude(self._attitude)

    def _card(self, parent: tk.Misc) -> tk.Frame:
        return tk.Frame(
            parent,
            bg=self._theme.surface,
            highlightthickness=1,
            highlightbackground=self._theme.border,
        )

    def update_position(self, state: PositionPresentationState) -> None:
        self._position = state
        fix_names = {1: "none", 2: "2D", 3: "3D"}
        values = {
            "latitude": self._format(state.latitude_deg, ".5f"),
            "longitude": self._format(state.longitude_deg, ".5f"),
            "altitude": self._format(state.altitude_ft, ".0f"),
            "fix": "--" if state.fix_mode is None else fix_names.get(state.fix_mode, str(state.fix_mode)),
            "satellites": "--" if state.satellites_used is None else str(state.satellites_used),
            "accuracy": self._format(state.accuracy_m, ".1f"),
        }
        for key, value in values.items():
            self._position_labels[key].configure(text=value)

    def update_attitude(self, state: AttitudePresentationState) -> None:
        self._attitude = state
        self._heading_label.configure(text="--°" if state.heading_deg is None else f"{state.heading_deg:03.0f}°")
        self._pitch_label.configure(text="PITCH --°" if state.pitch_deg is None else f"PITCH {state.pitch_deg:+.1f}°")
        self._roll_label.configure(text="ROLL --°" if state.roll_deg is None else f"ROLL {state.roll_deg:+.1f}°")
        self._paint_compass(state.heading_deg)
        self._paint_attitude(state.pitch_deg, state.roll_deg)

    def _paint_compass(self, heading: float | None) -> None:
        canvas = self._heading_canvas
        canvas.delete("all")
        cx, cy, radius = 105, 60, 48
        canvas.create_oval(
            cx - radius,
            cy - radius,
            cx + radius,
            cy + radius,
            outline=self._theme.border,
            width=2,
        )
        for label, degrees in (("N", 0), ("E", 90), ("S", 180), ("W", 270)):
            angle = math.radians(degrees - 90)
            canvas.create_text(
                cx + 36 * math.cos(angle),
                cy + 36 * math.sin(angle),
                text=label,
                fill=self._theme.accent_warning if label == "N" else self._theme.text_muted,
                font=("Sans", 9, "bold"),
            )
        if heading is None:
            return
        angle = math.radians(heading - 90)
        x = cx + 30 * math.cos(angle)
        y = cy + 30 * math.sin(angle)
        canvas.create_line(cx, cy, x, y, fill=self._theme.accent_warning, width=4, arrow=tk.LAST)
        canvas.create_oval(
            cx - 4,
            cy - 4,
            cx + 4,
            cy + 4,
            fill=self._theme.accent_warning,
            outline="",
        )

    def _paint_attitude(self, pitch: float | None, roll: float | None) -> None:
        canvas = self._attitude_canvas
        canvas.delete("all")
        width, height = 250, 100
        cx, cy = width / 2, height / 2
        canvas.create_rectangle(0, 0, width, height, fill=self._theme.surface, outline="")
        if pitch is None or roll is None:
            canvas.create_line(45, cy, width - 45, cy, fill=self._theme.border, width=2)
            return
        pitch_offset = max(-30.0, min(30.0, pitch)) * 1.2
        angle = math.radians(-roll)
        half = 90
        dx = half * math.cos(angle)
        dy = half * math.sin(angle)
        horizon_y = cy + pitch_offset
        canvas.create_line(
            cx - dx,
            horizon_y - dy,
            cx + dx,
            horizon_y + dy,
            fill=self._theme.accent_primary,
            width=4,
        )
        canvas.create_line(cx - 18, cy, cx + 18, cy, fill=self._theme.text, width=2)
        canvas.create_line(cx, cy - 7, cx, cy + 7, fill=self._theme.text, width=2)
        if abs(roll) >= 20 or abs(pitch) >= 20:
            canvas.create_text(
                width - 12,
                12,
                text="!",
                fill=self._theme.accent_danger,
                font=("Sans", 13, "bold"),
            )

    @staticmethod
    def _format(value: float | None, spec: str) -> str:
        return "--" if value is None else format(value, spec)
