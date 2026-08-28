# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Full off-road navigation and attitude panel for orcUi."""

from __future__ import annotations

import math
import tkinter as tk
from collections.abc import Callable

from apps.orcUi.navigation_presenter import AttitudePresentationState, PositionPresentationState

BG = "#05090d"
PANEL = "#0b1117"
BORDER = "#25313b"
TEXT = "#edf2f5"
MUTED = "#89959e"
YELLOW = "#d6ad22"
BLUE = "#168bd1"
GREEN = "#84ce1f"
RED = "#f15a16"


class OffRoadPanel(tk.Frame):
    """Large off-road instrument panel driven only by presentation state."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        on_back: Callable[[], None],
        position: PositionPresentationState | None = None,
        attitude: AttitudePresentationState | None = None,
    ) -> None:
        super().__init__(parent, bg=BG)
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
        self.grid_rowconfigure(1, weight=1)

        header = tk.Frame(self, bg=BG)
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 6))
        tk.Button(header, text="‹ HOME", command=on_back, bg="#101820", fg=TEXT,
                  relief=tk.FLAT, bd=0, font=("Sans", 10, "bold"), padx=14, pady=6).pack(side=tk.LEFT)
        tk.Label(header, text="OFF-ROAD", fg=YELLOW, bg=BG,
                 font=("Sans", 13, "bold")).pack(side=tk.LEFT, padx=14)
        tk.Label(header, text="NAVIGATION + ATTITUDE", fg=MUTED, bg=BG,
                 font=("Monospace", 9)).pack(side=tk.RIGHT, padx=4)

        instruments = tk.Frame(self, bg=BG)
        instruments.grid(row=1, column=0, sticky="nsew", padx=(0, 5))
        instruments.grid_rowconfigure(0, weight=1)
        instruments.grid_rowconfigure(1, weight=1)
        instruments.grid_columnconfigure(0, weight=1)

        compass = self._card(instruments)
        compass.grid(row=0, column=0, sticky="nsew", pady=(0, 5))
        tk.Label(compass, text="HEADING", fg=YELLOW, bg=PANEL,
                 font=("Sans", 9, "bold")).pack(pady=(8, 0))
        self._heading_canvas = tk.Canvas(compass, width=210, height=120, bg=PANEL, highlightthickness=0)
        self._heading_canvas.pack(expand=True)
        self._heading_label = tk.Label(compass, text="--°", fg=TEXT, bg=PANEL,
                                       font=("Sans", 18, "bold"))
        self._heading_label.pack(pady=(0, 7))

        attitude = self._card(instruments)
        attitude.grid(row=1, column=0, sticky="nsew", pady=(5, 0))
        tk.Label(attitude, text="ATTITUDE", fg=BLUE, bg=PANEL,
                 font=("Sans", 9, "bold")).pack(pady=(8, 0))
        self._attitude_canvas = tk.Canvas(attitude, width=250, height=100, bg=PANEL, highlightthickness=0)
        self._attitude_canvas.pack(expand=True)
        values = tk.Frame(attitude, bg=PANEL)
        values.pack(pady=(0, 7))
        self._pitch_label = tk.Label(values, text="PITCH --°", fg=TEXT, bg=PANEL, font=("Sans", 11, "bold"))
        self._pitch_label.pack(side=tk.LEFT, padx=14)
        self._roll_label = tk.Label(values, text="ROLL --°", fg=TEXT, bg=PANEL, font=("Sans", 11, "bold"))
        self._roll_label.pack(side=tk.LEFT, padx=14)

        position_card = self._card(self)
        position_card.grid(row=1, column=1, sticky="nsew", padx=(5, 0))
        tk.Label(position_card, text="POSITION", fg=GREEN, bg=PANEL,
                 font=("Sans", 10, "bold")).pack(anchor="w", padx=16, pady=(14, 8))
        grid = tk.Frame(position_card, bg=PANEL)
        grid.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 12))
        grid.grid_columnconfigure(1, weight=1)
        for row, (key, label, unit) in enumerate((
            ("latitude", "Latitude", "°"),
            ("longitude", "Longitude", "°"),
            ("altitude", "Altitude", "ft"),
            ("fix", "GPS fix", ""),
            ("satellites", "Satellites", "used"),
            ("accuracy", "Accuracy", "m"),
        )):
            tk.Label(grid, text=label, fg=MUTED, bg=PANEL, font=("Sans", 10)).grid(row=row, column=0, sticky="w", pady=8)
            value = tk.Label(grid, text="--", fg=TEXT, bg=PANEL, font=("Sans", 15, "bold"))
            value.grid(row=row, column=1, sticky="e", padx=8, pady=8)
            tk.Label(grid, text=unit, fg=MUTED, bg=PANEL, font=("Monospace", 8)).grid(row=row, column=2, sticky="w", pady=8)
            self._position_labels[key] = value

        self.update_position(self._position)
        self.update_attitude(self._attitude)

    @staticmethod
    def _card(parent: tk.Misc) -> tk.Frame:
        return tk.Frame(parent, bg=PANEL, highlightthickness=1, highlightbackground=BORDER)

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
        c = self._heading_canvas
        c.delete("all")
        cx, cy, radius = 105, 60, 48
        c.create_oval(cx-radius, cy-radius, cx+radius, cy+radius, outline="#33414c", width=2)
        for label, degrees in (("N", 0), ("E", 90), ("S", 180), ("W", 270)):
            angle = math.radians(degrees - 90)
            c.create_text(cx + 36*math.cos(angle), cy + 36*math.sin(angle), text=label,
                          fill=YELLOW if label == "N" else MUTED, font=("Sans", 9, "bold"))
        if heading is None:
            return
        angle = math.radians(heading - 90)
        x = cx + 30 * math.cos(angle)
        y = cy + 30 * math.sin(angle)
        c.create_line(cx, cy, x, y, fill=YELLOW, width=4, arrow=tk.LAST)
        c.create_oval(cx-4, cy-4, cx+4, cy+4, fill=YELLOW, outline="")

    def _paint_attitude(self, pitch: float | None, roll: float | None) -> None:
        c = self._attitude_canvas
        c.delete("all")
        width, height = 250, 100
        cx, cy = width / 2, height / 2
        c.create_rectangle(0, 0, width, height, outline="")
        if pitch is None or roll is None:
            c.create_line(45, cy, width-45, cy, fill="#33414c", width=2)
            return
        pitch_offset = max(-30.0, min(30.0, pitch)) * 1.2
        angle = math.radians(-roll)
        half = 90
        dx = half * math.cos(angle)
        dy = half * math.sin(angle)
        horizon_y = cy + pitch_offset
        c.create_line(cx-dx, horizon_y-dy, cx+dx, horizon_y+dy, fill=BLUE, width=4)
        c.create_line(cx-18, cy, cx+18, cy, fill=TEXT, width=2)
        c.create_line(cx, cy-7, cx, cy+7, fill=TEXT, width=2)
        if abs(roll) >= 20 or abs(pitch) >= 20:
            c.create_text(width-12, 12, text="!", fill=RED, font=("Sans", 13, "bold"))

    @staticmethod
    def _format(value: float | None, spec: str) -> str:
        return "--" if value is None else format(value, spec)
