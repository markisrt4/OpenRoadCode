# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Full-screen vehicle telemetry panel for orcUi."""

from __future__ import annotations

import math
import tkinter as tk
from collections.abc import Callable

from apps.orcUi.vehicle_presenter import VehiclePresentationState

BG = "#05090d"
PANEL = "#0b1117"
BORDER = "#25313b"
TEXT = "#edf2f5"
MUTED = "#89959e"
GREEN = "#84ce1f"
BLUE = "#168bd1"
RED = "#f15a16"
YELLOW = "#d6ad22"


class VehiclePanel(tk.Frame):
    """Large live vehicle dashboard using presentation-layer values only."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        on_back: Callable[[], None],
        state: VehiclePresentationState | None = None,
    ) -> None:
        super().__init__(parent, bg=BG)
        self._state = state or VehiclePresentationState()
        self._value_labels: dict[str, tk.Label] = {}
        self._speed_canvas: tk.Canvas
        self._rpm_canvas: tk.Canvas
        self._speed_value: tk.Label
        self._rpm_value: tk.Label

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = tk.Frame(self, bg=BG)
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 6))
        tk.Button(
            header,
            text="‹ HOME",
            command=on_back,
            bg="#101820",
            fg=TEXT,
            activebackground="#17232d",
            activeforeground=TEXT,
            relief=tk.FLAT,
            bd=0,
            font=("Sans", 10, "bold"),
            padx=14,
            pady=6,
        ).pack(side=tk.LEFT)
        tk.Label(
            header,
            text="VEHICLE",
            fg=GREEN,
            bg=BG,
            font=("Sans", 13, "bold"),
        ).pack(side=tk.LEFT, padx=14)
        tk.Label(
            header,
            text="LIVE TELEMETRY",
            fg=MUTED,
            bg=BG,
            font=("Monospace", 9),
        ).pack(side=tk.RIGHT, padx=4)

        gauges = tk.Frame(self, bg=BG)
        gauges.grid(row=1, column=0, sticky="nsew", padx=(0, 5))
        gauges.grid_columnconfigure(0, weight=1)
        gauges.grid_columnconfigure(1, weight=1)
        gauges.grid_rowconfigure(0, weight=1)
        self._build_gauge(gauges, 0, "SPEED", "MPH", BLUE, 160, "speed")
        self._build_gauge(gauges, 1, "ENGINE", "RPM", GREEN, 8000, "rpm")

        metrics = tk.Frame(
            self,
            bg=PANEL,
            highlightthickness=1,
            highlightbackground=BORDER,
        )
        metrics.grid(row=1, column=1, sticky="nsew", padx=(5, 0))
        metrics.grid_columnconfigure(0, weight=1)
        metrics.grid_columnconfigure(1, weight=1)

        specs = (
            ("boost", "BOOST", "PSI", RED),
            ("coolant", "COOLANT", "°F", BLUE),
            ("throttle", "THROTTLE", "%", YELLOW),
            ("fuel", "FUEL", "%", GREEN),
            ("voltage", "VOLTAGE", "V", TEXT),
        )
        for index, spec in enumerate(specs):
            row, column = divmod(index, 2)
            self._build_metric(metrics, row, column, *spec)

        self.update_state(self._state)

    def _build_gauge(
        self,
        parent: tk.Frame,
        column: int,
        title: str,
        unit: str,
        accent: str,
        maximum: float,
        key: str,
    ) -> None:
        card = tk.Frame(
            parent,
            bg=PANEL,
            highlightthickness=1,
            highlightbackground=BORDER,
        )
        card.grid(row=0, column=column, sticky="nsew", padx=(0, 5) if column == 0 else (5, 0))
        tk.Label(card, text=title, fg=accent, bg=PANEL, font=("Sans", 10, "bold")).pack(pady=(12, 0))
        canvas = tk.Canvas(card, width=215, height=150, bg=PANEL, highlightthickness=0)
        canvas.pack(expand=True)
        canvas._orc_maximum = maximum  # type: ignore[attr-defined]
        canvas._orc_accent = accent  # type: ignore[attr-defined]
        canvas._orc_key = key  # type: ignore[attr-defined]
        value = tk.Label(card, text="--", fg=TEXT, bg=PANEL, font=("Sans", 30, "bold"))
        value.pack(pady=(0, 0))
        tk.Label(card, text=unit, fg=MUTED, bg=PANEL, font=("Monospace", 9)).pack(pady=(0, 14))
        if key == "speed":
            self._speed_canvas = canvas
            self._speed_value = value
        else:
            self._rpm_canvas = canvas
            self._rpm_value = value

    def _build_metric(
        self,
        parent: tk.Frame,
        row: int,
        column: int,
        key: str,
        title: str,
        unit: str,
        accent: str,
    ) -> None:
        card = tk.Frame(parent, bg=PANEL)
        card.grid(row=row, column=column, sticky="nsew", padx=12, pady=10)
        tk.Label(card, text=title, fg=accent, bg=PANEL, font=("Sans", 9, "bold")).pack(anchor="w")
        value = tk.Label(card, text="--", fg=TEXT, bg=PANEL, font=("Sans", 24, "bold"))
        value.pack(anchor="w", pady=(4, 0))
        tk.Label(card, text=unit, fg=MUTED, bg=PANEL, font=("Monospace", 8)).pack(anchor="w")
        self._value_labels[key] = value

    def update_state(self, state: VehiclePresentationState) -> None:
        """Refresh all visible gauges from the latest presentation state."""
        self._state = state
        self._speed_value.configure(text=self._format(state.speed_mph, ".0f"))
        self._rpm_value.configure(text=self._format(state.engine_speed_rpm, ".0f"))
        self._paint_gauge(self._speed_canvas, state.speed_mph)
        self._paint_gauge(self._rpm_canvas, state.engine_speed_rpm)

        values = {
            "boost": self._format(state.boost_psi, ".1f"),
            "coolant": self._format(state.coolant_temperature_f, ".0f"),
            "throttle": self._format(state.throttle_percent, ".0f"),
            "fuel": self._format(state.fuel_percent, ".0f"),
            "voltage": self._format(state.control_voltage_v, ".1f"),
        }
        for key, text in values.items():
            self._value_labels[key].configure(text=text)

    @staticmethod
    def _format(value: float | None, spec: str) -> str:
        return "--" if value is None else format(value, spec)

    @staticmethod
    def _paint_gauge(canvas: tk.Canvas, value: float | None) -> None:
        canvas.delete("all")
        cx, cy, radius = 108, 122, 88
        start_deg, sweep_deg = 210.0, 240.0
        maximum = float(canvas._orc_maximum)  # type: ignore[attr-defined]
        accent = str(canvas._orc_accent)  # type: ignore[attr-defined]

        canvas.create_arc(
            cx - radius,
            cy - radius,
            cx + radius,
            cy + radius,
            start=-30,
            extent=240,
            style=tk.ARC,
            outline="#33414c",
            width=10,
        )
        for index in range(9):
            angle = math.radians(start_deg - sweep_deg * index / 8.0)
            outer_x = cx + radius * math.cos(angle)
            outer_y = cy - radius * math.sin(angle)
            inner_x = cx + (radius - 12) * math.cos(angle)
            inner_y = cy - (radius - 12) * math.sin(angle)
            canvas.create_line(inner_x, inner_y, outer_x, outer_y, fill=MUTED, width=2)

        if value is None:
            return
        fraction = max(0.0, min(1.0, value / maximum))
        angle = math.radians(start_deg - sweep_deg * fraction)
        needle_x = cx + (radius - 20) * math.cos(angle)
        needle_y = cy - (radius - 20) * math.sin(angle)
        canvas.create_line(cx, cy, needle_x, needle_y, fill=accent, width=4)
        canvas.create_oval(cx - 6, cy - 6, cx + 6, cy + 6, fill=accent, outline="")
