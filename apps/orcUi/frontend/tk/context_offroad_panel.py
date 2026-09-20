# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Off-road context page used by the cockpit context rail."""

from __future__ import annotations

import math
import tkinter as tk

from apps.orcUi.navigation_presenter import AttitudePresentationState, PositionPresentationState
from apps.orcUi.vehicle_presenter import VehiclePresentationState
from ui.theme import ThemeBundle
from .offroad_widgets import PitchIndicator, RollIndicator
from .shell_metrics import FONT_BODY, FONT_CONTROL, FONT_SMALL


class ContextOffroadPanel(tk.Frame):
    """Render compact GPS, heading, and attitude information."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        theme: ThemeBundle,
        vehicle: VehiclePresentationState,
        position: PositionPresentationState,
        attitude: AttitudePresentationState,
    ) -> None:
        self._theme = theme
        self._vehicle = vehicle
        self._position = position
        self._attitude = attitude
        self._value_labels: dict[str, tk.Label] = {}
        self._heading_canvas: tk.Canvas | None = None
        self._roll_indicator: RollIndicator | None = None
        self._pitch_indicator: PitchIndicator | None = None
        super().__init__(parent, bg=theme.ui.surface)
        self._build()
        self._paint()

    def update_vehicle(self, state: VehiclePresentationState) -> None:
        self._vehicle = state
        self._paint()

    def update_position(self, state: PositionPresentationState) -> None:
        self._position = state
        self._paint()

    def update_attitude(self, state: AttitudePresentationState) -> None:
        self._attitude = state
        self._paint()

    def _build(self) -> None:
        ui = self._theme.ui
        self.pack(fill=tk.BOTH, expand=True)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        status = self._card()
        status.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(2, 6))
        status.grid_columnconfigure(1, weight=1)
        tk.Label(status, text="GPS", fg=ui.text_muted, bg=ui.surface, font=("Sans", FONT_CONTROL, "bold")).grid(
            row=0, column=0, padx=(8, 4), pady=5
        )
        self._value_labels["fix"] = tk.Label(
            status, text="NO FIX", fg=ui.accent_danger, bg=ui.surface, font=("Sans", FONT_BODY, "bold")
        )
        self._value_labels["fix"].grid(row=0, column=1, sticky="w", pady=5)
        self._value_labels["accuracy"] = tk.Label(
            status, text="± -- m", fg=ui.text_muted, bg=ui.surface, font=("Sans", FONT_SMALL, "bold")
        )
        self._value_labels["accuracy"].grid(row=0, column=2, padx=(4, 8), pady=5)

        heading_card = self._card()
        heading_card.grid(row=1, column=0, sticky="nsew", padx=(0, 3), pady=(0, 6))
        tk.Label(heading_card, text="HEADING", fg=ui.accent_warning, bg=ui.surface, font=("Sans", FONT_SMALL, "bold")).pack(
            pady=(5, 0)
        )
        self._heading_canvas = tk.Canvas(
            heading_card, width=118, height=86, bg=ui.surface, highlightthickness=0
        )
        self._heading_canvas.pack(fill=tk.BOTH, expand=True, padx=4)
        self._value_labels["heading"] = tk.Label(
            heading_card, text="--", fg=ui.text, bg=ui.surface, font=("Sans", FONT_BODY + 2, "bold")
        )
        self._value_labels["heading"].pack(pady=(0, 5))

        slope_card = self._card()
        slope_card.grid(row=1, column=1, sticky="nsew", padx=(3, 0), pady=(0, 6))
        tk.Label(
            slope_card,
            text="ROLL / PITCH",
            fg=ui.accent_primary,
            bg=ui.surface,
            font=("Sans", FONT_SMALL, "bold"),
        ).pack(pady=(5, 0))
        indicators = tk.Frame(slope_card, bg=ui.surface)
        indicators.pack(fill=tk.BOTH, expand=True, padx=4)
        indicators.grid_columnconfigure(0, weight=1)
        indicators.grid_columnconfigure(1, weight=1)
        self._roll_indicator = RollIndicator(indicators, theme=self._theme)
        self._roll_indicator.grid(row=0, column=0, sticky="nsew", padx=(0, 2))
        self._pitch_indicator = PitchIndicator(indicators, theme=self._theme)
        self._pitch_indicator.grid(row=0, column=1, sticky="nsew", padx=(2, 0))
        grade = tk.Frame(slope_card, bg=ui.surface)
        grade.pack(fill=tk.X, padx=10, pady=(0, 5))
        tk.Label(
            grade,
            text="GRADE",
            fg=ui.text_muted,
            bg=ui.surface,
            font=("Sans", FONT_SMALL, "bold"),
        ).pack(side=tk.LEFT)
        self._value_labels["grade"] = tk.Label(
            grade,
            text="--",
            fg=ui.text,
            bg=ui.surface,
            font=("Sans", FONT_BODY + 1, "bold"),
        )
        self._value_labels["grade"].pack(side=tk.RIGHT)

        self._metric_card("ALTITUDE", "altitude", "ft").grid(
            row=2, column=0, sticky="nsew", padx=(0, 3), pady=(0, 6)
        )
        self._metric_card("SPEED", "speed", "mph").grid(
            row=2, column=1, sticky="nsew", padx=(3, 0), pady=(0, 6)
        )
        footer = self._card()
        footer.grid(row=3, column=0, columnspan=2, sticky="ew")
        footer.grid_columnconfigure(0, weight=1)
        self._value_labels["coordinates"] = tk.Label(
            footer, text="--", fg=ui.text, bg=ui.surface, font=("Monospace", FONT_SMALL, "bold"), anchor="w"
        )
        self._value_labels["coordinates"].grid(row=0, column=0, sticky="ew", padx=(8, 4), pady=6)
        self._value_labels["satellites"] = tk.Label(
            footer, text="-- sat", fg=ui.text_muted, bg=ui.surface, font=("Sans", FONT_CONTROL, "bold")
        )
        self._value_labels["satellites"].grid(row=0, column=1, sticky="e", padx=(4, 8), pady=6)

    def _card(self) -> tk.Frame:
        ui = self._theme.ui
        return tk.Frame(self, bg=ui.surface, highlightthickness=1, highlightbackground=ui.border)

    def _metric_card(self, title: str, key: str, unit: str) -> tk.Frame:
        ui = self._theme.ui
        card = self._card()
        tk.Label(card, text=title, fg=ui.text_muted, bg=ui.surface, font=("Sans", FONT_SMALL, "bold")).pack(pady=(5, 0))
        row = tk.Frame(card, bg=ui.surface)
        row.pack(pady=(0, 5))
        value = tk.Label(row, text="--", fg=ui.text, bg=ui.surface, font=("Sans", FONT_BODY + 4, "bold"))
        value.pack(side=tk.LEFT)
        tk.Label(row, text=unit, fg=ui.text_muted, bg=ui.surface, font=("Sans", FONT_SMALL)).pack(
            side=tk.LEFT, padx=(3, 0), pady=(6, 0)
        )
        self._value_labels[key] = value
        return card

    def _paint(self) -> None:
        ui = self._theme.ui
        heading = self._attitude.heading_deg
        heading_text = "--" if heading is None else f"{_cardinal_direction(heading)} {heading:03.0f}°"
        coordinates = (
            "--"
            if self._position.latitude_deg is None or self._position.longitude_deg is None
            else f"{self._position.latitude_deg:.5f}°  {self._position.longitude_deg:.5f}°"
        )
        pitch = self._attitude.pitch_deg
        grade = None if pitch is None else math.tan(math.radians(pitch)) * 100.0
        values = {
            "heading": heading_text,
            "grade": "--" if grade is None else f"{grade:+.1f}%",
            "altitude": _format(self._position.altitude_ft, ".0f"),
            "speed": _format(self._vehicle.speed_mph, ".0f"),
            "fix": _fix_text(self._position.fix_mode),
            "accuracy": "± -- m" if self._position.accuracy_m is None else f"± {self._position.accuracy_m:.1f} m",
            "coordinates": coordinates,
            "satellites": "-- sat" if self._position.satellites_used is None else f"{self._position.satellites_used} sat",
        }
        for key, value in values.items():
            self._value_labels[key].configure(text=value)
        if self._roll_indicator is not None:
            self._roll_indicator.set_value(self._attitude.roll_deg)
        if self._pitch_indicator is not None:
            self._pitch_indicator.set_value(pitch)
        self._value_labels["fix"].configure(fg=_fix_color(self._theme, self._position.fix_mode))
        self._paint_compass(heading)

    def _paint_compass(self, heading: float | None) -> None:
        canvas = self._heading_canvas
        if canvas is None:
            return
        ui = self._theme.ui
        canvas.delete("all")
        width, height = max(90, canvas.winfo_width()), max(70, canvas.winfo_height())
        cx, cy, radius = width / 2, height / 2, min(width, height) * 0.36
        canvas.create_oval(cx - radius, cy - radius, cx + radius, cy + radius, outline=ui.border, width=2)
        for label, degrees in (("N", 0), ("E", 90), ("S", 180), ("W", 270)):
            angle = math.radians(degrees - 90)
            canvas.create_text(
                cx + radius * 0.72 * math.cos(angle), cy + radius * 0.72 * math.sin(angle),
                text=label, fill=ui.accent_warning if label == "N" else ui.text_muted,
                font=("Sans", FONT_SMALL, "bold"),
            )
        if heading is None:
            return
        angle = math.radians(heading - 90)
        canvas.create_line(
            cx, cy, cx + radius * 0.62 * math.cos(angle), cy + radius * 0.62 * math.sin(angle),
            fill=ui.accent_warning, width=3, arrow=tk.LAST,
        )
        canvas.create_oval(cx - 3, cy - 3, cx + 3, cy + 3, fill=ui.accent_warning, outline="")

def _fix_text(fix_mode: int | None) -> str:
    return {1: "NO FIX", 2: "2D FIX", 3: "3D FIX"}.get(fix_mode, "NO FIX")


def _fix_color(theme: ThemeBundle, fix_mode: int | None) -> str:
    if fix_mode is not None and fix_mode >= 3:
        return theme.ui.accent_success
    if fix_mode == 2:
        return theme.ui.accent_warning
    return theme.ui.accent_danger


def _cardinal_direction(heading_deg: float) -> str:
    directions = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")
    return directions[int((heading_deg % 360.0 + 22.5) // 45.0) % len(directions)]


def _signed(value: float | None) -> str:
    return "--" if value is None else f"{value:+.1f}°"


def _format(value: float | None, spec: str) -> str:
    return "--" if value is None else format(value, spec)
