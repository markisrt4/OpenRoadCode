# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Switchable secondary context rail for the ORC cockpit home screen."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from dataclasses import dataclass

from apps.orcUi.navigation_presenter import PositionPresentationState
from apps.orcUi.vehicle_presenter import VehiclePresentationState
from frontends.tk.automotive.vehicle_gauge_widgets import (
    GearIndicator,
    LinearGauge,
    RoundGauge,
)

PANEL = "#0b1117"
BORDER = "#25313b"
TEXT = "#edf2f5"
MUTED = "#89959e"
GREEN = "#84ce1f"
BLUE = "#168bd1"
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
        self._vehicle_gauges: dict[str, RoundGauge | LinearGauge | GearIndicator] = {}
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
        self._offroad_value_labels.clear()
        page = self._pages[self._page_index]
        self._title.configure(text=page.name, fg=page.accent)
        page.builder(self._body)
        dots = tk.Frame(self._body, bg=PANEL)
        dots.pack(side=tk.BOTTOM, pady=(4, 0))
        for index in range(len(self._pages)):
            tk.Label(dots, text="●" if index == self._page_index else "·", fg=page.accent if index == self._page_index else MUTED, bg=PANEL, font=("Sans", 9)).pack(side=tk.LEFT, padx=2)

    def _build_vehicle(self, parent: tk.Frame) -> None:
        """Build a glanceable miniature instrument cluster for the home rail."""
        cluster = tk.Frame(parent, bg=PANEL)
        cluster.pack(fill=tk.BOTH, expand=True)
        cluster.grid_columnconfigure(0, weight=1)
        cluster.grid_columnconfigure(1, weight=1)
        cluster.grid_rowconfigure(0, weight=3)
        cluster.grid_rowconfigure(1, weight=3)
        cluster.grid_rowconfigure(2, weight=1)

        rpm = RoundGauge(
            cluster,
            title="RPM",
            unit="x1000",
            minimum=0.0,
            maximum=8.0,
            major_step=2.0,
            caution_start=6.0,
            danger_start=6.8,
            precision=1,
            size=122,
        )
        rpm.grid(row=0, column=0, sticky="nsew", padx=(0, 2), pady=(0, 2))

        boost = RoundGauge(
            cluster,
            title="BOOST",
            unit="PSI",
            minimum=-15.0,
            maximum=25.0,
            major_step=10.0,
            caution_start=18.0,
            danger_start=22.0,
            precision=1,
            size=122,
        )
        boost.grid(row=0, column=1, sticky="nsew", padx=(2, 0), pady=(0, 2))

        speed = RoundGauge(
            cluster,
            title="SPEED",
            unit="MPH",
            minimum=0.0,
            maximum=160.0,
            major_step=40.0,
            precision=0,
            size=122,
        )
        speed.grid(row=1, column=0, sticky="nsew", padx=(0, 2), pady=2)

        gear = GearIndicator(cluster, width=122, height=122)
        gear.grid(row=1, column=1, sticky="nsew", padx=(2, 0), pady=2)

        coolant = LinearGauge(
            cluster,
            title="Coolant",
            unit="°F",
            minimum=100.0,
            maximum=260.0,
            caution_high=225.0,
            danger_high=240.0,
            icon="coolant",
            precision=0,
            width=250,
            height=64,
        )
        coolant.grid(
            row=2,
            column=0,
            columnspan=2,
            sticky="nsew",
            pady=(2, 0),
        )

        self._vehicle_gauges.update(
            rpm=rpm,
            boost=boost,
            speed=speed,
            gear=gear,
            coolant=coolant,
        )
        self._paint_vehicle_values()

    def _paint_vehicle_values(self) -> None:
        state = self._vehicle_state
        values: dict[str, float | str | None] = {
            "rpm": None if state.engine_speed_rpm is None else state.engine_speed_rpm / 1000.0,
            "boost": state.boost_psi,
            "speed": state.speed_mph,
            "gear": state.gear,
            "coolant": state.coolant_temperature_f,
        }
        for key, value in values.items():
            gauge = self._vehicle_gauges.get(key)
            if gauge is not None:
                gauge.set_value(value)

    def _build_trip(self, parent: tk.Frame) -> None:
        self._metric_table(parent, (("distance", "Distance", "mi"), ("elapsed", "Elapsed", ""), ("average", "Avg speed", "MPH"), ("moving", "Moving", ""), ("fuel_used", "Fuel used", "gal"), ("economy", "Economy", "MPG")))

    def _build_offroad(self, parent: tk.Frame) -> None:
        self._metric_table(parent, (("latitude", "Latitude", "°"), ("longitude", "Longitude", "°"), ("altitude", "Altitude", "ft"), ("fix", "GPS fix", ""), ("satellites", "Satellites", "used"), ("accuracy", "Accuracy", "m")), self._offroad_value_labels)
        self._paint_offroad_values()

    def _paint_offroad_values(self) -> None:
        state = self._position_state
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
            label = self._offroad_value_labels.get(key)
            if label is not None:
                label.configure(text=value)

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
