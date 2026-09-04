# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Switchable secondary context rail for the ORC cockpit home screen."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from dataclasses import dataclass

from apps.orcUi.navigation_presenter import PositionPresentationState
from apps.orcUi.vehicle_presenter import VehiclePresentationState
from frontends.tk.automotive import FuelLevelGauge
from frontends.tk.automotive.vehicle_gauge_widgets import LinearGauge, RoundGauge

PANEL = "#0b1117"
BORDER = "#25313b"
TEXT = "#edf2f5"
MUTED = "#89959e"
GREEN = "#84ce1f"
BLUE = "#168bd1"
RED = "#f15a16"
YELLOW = "#d6ad22"


@dataclass(frozen=True)
class ContextPage:
    name: str
    accent: str
    builder: Callable[[tk.Frame], None]


class ContextRail(tk.Frame):
    """Compact, user-switchable secondary information panel."""

    WIDTH = 300

    def __init__(self, parent: tk.Misc, on_expand: Callable[[str], None] | None = None) -> None:
        super().__init__(parent, bg=PANEL, width=self.WIDTH, highlightthickness=1, highlightbackground=BORDER)
        self.pack_propagate(False)
        self._on_expand = on_expand
        self._vehicle_state = VehiclePresentationState()
        self._position_state = PositionPresentationState()
        self._vehicle_gauges: dict[str, RoundGauge | LinearGauge | FuelLevelGauge] = {}
        self._gear_value_label: tk.Label | None = None
        self._offroad_value_labels: dict[str, tk.Label] = {}
        self._pages = (
            ContextPage("VEHICLE", GREEN, self._build_vehicle),
            ContextPage("TRIP", BLUE, self._build_trip),
            ContextPage("OFF-ROAD", YELLOW, self._build_offroad),
        )
        self._page_index = 0
        self._title: tk.Label
        self._body = tk.Frame(self, bg=PANEL)
        self._build_header()
        self._body.pack(fill=tk.BOTH, expand=True, padx=10, pady=(2, 10))
        self._show_page()

    @property
    def selected_page(self) -> str:
        return self._pages[self._page_index].name

    def update_vehicle_state(self, state: VehiclePresentationState) -> None:
        self._vehicle_state = state
        if self.selected_page == "VEHICLE":
            self._paint_vehicle_values()

    def update_position_state(self, state: PositionPresentationState) -> None:
        self._position_state = state
        if self.selected_page == "OFF-ROAD":
            self._paint_offroad_values()

    def _build_header(self) -> None:
        header = tk.Frame(self, bg=PANEL)
        header.pack(fill=tk.X, padx=8, pady=(7, 3))
        header.grid_columnconfigure(1, weight=1)
        self._title = tk.Label(header, text="", bg=PANEL, font=("Sans", 10, "bold"))
        self._nav_button(header, "‹", self._previous_page).grid(row=0, column=0, sticky="w")
        self._title.grid(row=0, column=1)
        controls = tk.Frame(header, bg=PANEL)
        controls.grid(row=0, column=2, sticky="e")
        if self._on_expand is not None:
            self._nav_button(controls, "□", self._expand_page, width=2, font_size=12).pack(side=tk.LEFT)
        self._nav_button(controls, "›", self._next_page).pack(side=tk.LEFT)

    @staticmethod
    def _nav_button(parent: tk.Misc, text: str, command: Callable[[], None], *, width: int = 3, font_size: int = 16) -> tk.Button:
        return tk.Button(parent, text=text, command=command, bg=PANEL, fg=TEXT, activebackground="#121b23", activeforeground=TEXT, relief=tk.FLAT, bd=0, width=width, font=("Sans", font_size, "bold"), cursor="hand2")

    def _expand_page(self) -> None:
        if self._on_expand is not None:
            self._on_expand(self.selected_page)

    def _previous_page(self) -> None:
        self._page_index = (self._page_index - 1) % len(self._pages)
        self._show_page()

    def _next_page(self) -> None:
        self._page_index = (self._page_index + 1) % len(self._pages)
        self._show_page()

    def _show_page(self) -> None:
        for child in self._body.winfo_children():
            child.destroy()
        self._vehicle_gauges.clear()
        self._gear_value_label = None
        self._offroad_value_labels.clear()
        page = self._pages[self._page_index]
        self._title.configure(text=page.name, fg=page.accent)
        page.builder(self._body)
        dots = tk.Frame(self._body, bg=PANEL)
        dots.pack(side=tk.BOTTOM, pady=(4, 0))
        for index in range(len(self._pages)):
            tk.Label(dots, text="●" if index == self._page_index else "·", fg=page.accent if index == self._page_index else MUTED, bg=PANEL, font=("Sans", 9)).pack(side=tk.LEFT, padx=2)

    def _build_vehicle(self, parent: tk.Frame) -> None:
        """Build the primary home instruments plus compact vehicle status."""
        cluster = tk.Frame(parent, bg=PANEL)
        cluster.pack(fill=tk.BOTH, expand=True)
        cluster.grid_columnconfigure(0, weight=1)
        cluster.grid_columnconfigure(1, weight=1)
        cluster.grid_rowconfigure(0, weight=3)
        cluster.grid_rowconfigure(1, weight=3)
        cluster.grid_rowconfigure(2, weight=1)

        rpm = RoundGauge(cluster, title="RPM", unit="x1000", minimum=0.0, maximum=8.0, major_step=1.0, caution_start=6.0, danger_start=6.8, precision=1, size=122)
        rpm.grid(row=0, column=0, sticky="nsew", padx=(0, 2), pady=(0, 2))
        speed = RoundGauge(cluster, title="SPEED", unit="MPH", minimum=0.0, maximum=160.0, major_step=40.0, precision=0, size=122)
        speed.grid(row=0, column=1, sticky="nsew", padx=(2, 0), pady=(0, 2))
        boost = RoundGauge(cluster, title="BOOST", unit="PSI", minimum=-15.0, maximum=25.0, major_step=5.0, caution_start=18.0, danger_start=22.0, precision=1, size=122)
        boost.grid(row=1, column=0, sticky="nsew", padx=(0, 2), pady=2)
        fuel = FuelLevelGauge(cluster, size=122)
        fuel.grid(row=1, column=1, sticky="nsew", padx=(2, 0), pady=2)

        status = tk.Frame(cluster, bg=PANEL)
        status.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=(2, 0))
        status.grid_columnconfigure(0, weight=1)
        coolant = LinearGauge(status, title="Coolant", unit="°F", minimum=100.0, maximum=260.0, caution_high=225.0, danger_high=240.0, icon="coolant", precision=0, width=190, height=58)
        coolant.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        gear = tk.Frame(status, bg=PANEL, highlightthickness=1, highlightbackground=BORDER)
        gear.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
        tk.Label(gear, text="GEAR", fg=MUTED, bg=PANEL, font=("Sans", 7, "bold")).pack(padx=10, pady=(4, 0))
        self._gear_value_label = tk.Label(gear, text="—", fg=RED, bg=PANEL, font=("Sans", 22, "bold"))
        self._gear_value_label.pack(padx=10, pady=(0, 3))
        self._vehicle_gauges.update(rpm=rpm, speed=speed, boost=boost, fuel=fuel, coolant=coolant)
        self._paint_vehicle_values()

    def _paint_vehicle_values(self) -> None:
        state = self._vehicle_state
        values: dict[str, float | None] = {
            "rpm": None if state.engine_speed_rpm is None else state.engine_speed_rpm / 1000.0,
            "speed": state.speed_mph,
            "boost": state.boost_psi,
            "fuel": state.fuel_percent,
            "coolant": state.coolant_temperature_f,
        }
        for key, value in values.items():
            gauge = self._vehicle_gauges.get(key)
            if gauge is not None:
                gauge.set_value(value)
        if self._gear_value_label is not None:
            self._gear_value_label.configure(text=state.gear or "—")

    def _build_trip(self, parent: tk.Frame) -> None:
        self._metric_table(parent, (("distance", "Distance", "mi"), ("elapsed", "Elapsed", ""), ("average", "Avg speed", "MPH"), ("moving", "Moving", ""), ("fuel_used", "Fuel used", "gal"), ("economy", "Economy", "MPG")))

    def _build_offroad(self, parent: tk.Frame) -> None:
        """Build a compact GPS instrument instead of a debug-style table."""
        panel = tk.Frame(parent, bg=PANEL)
        panel.pack(fill=tk.BOTH, expand=True)
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_columnconfigure(1, weight=1)
        panel.grid_rowconfigure(1, weight=1)

        status = tk.Frame(panel, bg=PANEL, highlightthickness=1, highlightbackground=BORDER)
        status.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(2, 7))
        status.grid_columnconfigure(1, weight=1)
        tk.Label(status, text="GPS", fg=MUTED, bg=PANEL, font=("Sans", 8, "bold")).grid(row=0, column=0, padx=(8, 4), pady=5)
        self._offroad_value_labels["fix"] = tk.Label(status, text="NO FIX", fg=YELLOW, bg=PANEL, font=("Sans", 10, "bold"))
        self._offroad_value_labels["fix"].grid(row=0, column=1, sticky="w", pady=5)
        self._offroad_value_labels["accuracy"] = tk.Label(status, text="± -- m", fg=MUTED, bg=PANEL, font=("Sans", 9, "bold"))
        self._offroad_value_labels["accuracy"].grid(row=0, column=2, padx=(4, 8), pady=5)

        coordinates = tk.Frame(panel, bg=PANEL, highlightthickness=1, highlightbackground=BORDER)
        coordinates.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(0, 7))
        coordinates.grid_columnconfigure(0, weight=1)
        tk.Label(coordinates, text="POSITION", fg=YELLOW, bg=PANEL, font=("Sans", 8, "bold"), anchor="w").grid(row=0, column=0, sticky="w", padx=9, pady=(7, 2))
        self._offroad_value_labels["latitude"] = tk.Label(coordinates, text="--", fg=TEXT, bg=PANEL, font=("Sans", 15, "bold"), anchor="w")
        self._offroad_value_labels["latitude"].grid(row=1, column=0, sticky="ew", padx=9)
        self._offroad_value_labels["longitude"] = tk.Label(coordinates, text="--", fg=TEXT, bg=PANEL, font=("Sans", 15, "bold"), anchor="w")
        self._offroad_value_labels["longitude"].grid(row=2, column=0, sticky="ew", padx=9, pady=(0, 7))

        altitude = self._offroad_metric_card(panel, "ALTITUDE", "altitude", "ft")
        altitude.grid(row=2, column=0, sticky="nsew", padx=(0, 3))
        satellites = self._offroad_metric_card(panel, "SATELLITES", "satellites", "used")
        satellites.grid(row=2, column=1, sticky="nsew", padx=(3, 0))
        self._paint_offroad_values()

    def _offroad_metric_card(self, parent: tk.Misc, title: str, key: str, unit: str) -> tk.Frame:
        card = tk.Frame(parent, bg=PANEL, highlightthickness=1, highlightbackground=BORDER)
        tk.Label(card, text=title, fg=MUTED, bg=PANEL, font=("Sans", 7, "bold")).pack(pady=(6, 0))
        value_row = tk.Frame(card, bg=PANEL)
        value_row.pack(pady=(0, 6))
        value = tk.Label(value_row, text="--", fg=TEXT, bg=PANEL, font=("Sans", 15, "bold"))
        value.pack(side=tk.LEFT)
        tk.Label(value_row, text=unit, fg=MUTED, bg=PANEL, font=("Sans", 7)).pack(side=tk.LEFT, padx=(3, 0), pady=(6, 0))
        self._offroad_value_labels[key] = value
        return card

    def _paint_offroad_values(self) -> None:
        state = self._position_state
        fix_names = {1: "NO FIX", 2: "2D FIX", 3: "3D FIX"}
        values = {
            "latitude": "--" if state.latitude_deg is None else f"LAT  {state.latitude_deg:.5f}°",
            "longitude": "--" if state.longitude_deg is None else f"LON  {state.longitude_deg:.5f}°",
            "altitude": self._format(state.altitude_ft, ".0f"),
            "fix": "NO FIX" if state.fix_mode is None else fix_names.get(state.fix_mode, str(state.fix_mode)),
            "satellites": "--" if state.satellites_used is None else str(state.satellites_used),
            "accuracy": "± -- m" if state.accuracy_m is None else f"± {state.accuracy_m:.1f} m",
        }
        for key, value in values.items():
            label = self._offroad_value_labels.get(key)
            if label is not None:
                label.configure(text=value)
        fix_label = self._offroad_value_labels.get("fix")
        if fix_label is not None:
            fix_label.configure(fg=GREEN if state.fix_mode is not None and state.fix_mode >= 2 else YELLOW)

    @staticmethod
    def _format(value: float | None, spec: str) -> str:
        return "--" if value is None else format(value, spec)

    @staticmethod
    def _metric_table(parent: tk.Frame, metrics: tuple[tuple[str, str, str], ...], value_labels: dict[str, tk.Label] | None = None) -> None:
        grid = tk.Frame(parent, bg=PANEL)
        grid.pack(fill=tk.BOTH, expand=True)
        grid.grid_columnconfigure(0, weight=2)
        grid.grid_columnconfigure(1, weight=1)
        grid.grid_columnconfigure(2, weight=1)
        for row, (key, label, unit) in enumerate(metrics):
            tk.Label(grid, text=label, fg=MUTED, bg=PANEL, font=("Sans", 9), anchor="w").grid(row=row, column=0, sticky="w", padx=(2, 4), pady=3)
            value = tk.Label(grid, text="--", fg=TEXT, bg=PANEL, font=("Sans", 12, "bold"), anchor="e")
            value.grid(row=row, column=1, sticky="e", padx=4, pady=3)
            if value_labels is not None:
                value_labels[key] = value
            tk.Label(grid, text=unit, fg=MUTED, bg=PANEL, font=("Sans", 8), anchor="w").grid(row=row, column=2, sticky="w", padx=(0, 2), pady=3)
