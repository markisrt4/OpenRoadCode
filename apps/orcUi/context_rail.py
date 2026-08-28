# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Switchable secondary context rail for the ORC cockpit home screen."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from dataclasses import dataclass

from apps.orcUi.vehicle_presenter import VehiclePresentationState


PANEL = "#0b1117"
BORDER = "#25313b"
TEXT = "#edf2f5"
MUTED = "#89959e"
GREEN = "#79c83d"
BLUE = "#3297e5"
YELLOW = "#d6ad22"


@dataclass(frozen=True)
class ContextPage:
    """Description of one context-rail page."""

    name: str
    accent: str
    builder: Callable[[tk.Frame], None]


class ContextRail(tk.Frame):
    """Compact, user-switchable secondary information panel."""

    WIDTH = 300

    def __init__(
        self,
        parent: tk.Misc,
        on_expand: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(parent, bg=PANEL, width=self.WIDTH, highlightthickness=1, highlightbackground=BORDER)
        self.grid_propagate(False)
        self._on_expand = on_expand
        self._vehicle_state = VehiclePresentationState()
        self._vehicle_value_labels: dict[str, tk.Label] = {}
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
        """Update the cached vehicle presentation state and visible metrics."""
        self._vehicle_state = state
        if self.selected_page == "VEHICLE":
            self._paint_vehicle_values()

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
        self._vehicle_value_labels.clear()
        page = self._pages[self._page_index]
        self._title.configure(text=page.name, fg=page.accent)
        page.builder(self._body)
        dots = tk.Frame(self._body, bg=PANEL)
        dots.pack(side=tk.BOTTOM, pady=(4, 0))
        for index in range(len(self._pages)):
            tk.Label(dots, text="●" if index == self._page_index else "·", fg=page.accent if index == self._page_index else MUTED, bg=PANEL, font=("Sans", 9)).pack(side=tk.LEFT, padx=2)

    def _build_vehicle(self, parent: tk.Frame) -> None:
        self._metric_table(parent, (("speed", "Speed", "MPH"), ("rpm", "RPM", "RPM"), ("boost", "Boost", "PSI"), ("coolant", "Coolant", "°F"), ("fuel", "Fuel", "%"), ("voltage", "Voltage", "V")), self._vehicle_value_labels)
        self._paint_vehicle_values()

    def _paint_vehicle_values(self) -> None:
        state = self._vehicle_state
        values = {
            "speed": self._format(state.speed_mph, ".0f"),
            "rpm": self._format(state.engine_speed_rpm, ".0f"),
            "boost": self._format(state.boost_psi, ".1f"),
            "coolant": self._format(state.coolant_temperature_f, ".0f"),
            "fuel": self._format(state.fuel_percent, ".0f"),
            "voltage": self._format(state.control_voltage_v, ".1f"),
        }
        for key, value in values.items():
            label = self._vehicle_value_labels.get(key)
            if label is not None:
                label.configure(text=value)

    def _build_trip(self, parent: tk.Frame) -> None:
        self._metric_table(parent, (("distance", "Distance", "mi"), ("elapsed", "Elapsed", ""), ("average", "Avg speed", "MPH"), ("moving", "Moving", ""), ("fuel_used", "Fuel used", "gal"), ("economy", "Economy", "MPG")))

    def _build_offroad(self, parent: tk.Frame) -> None:
        tk.Label(parent, text="N\n↑\n---°", fg=YELLOW, bg=PANEL, font=("Sans", 16, "bold"), justify=tk.CENTER).pack(pady=(4, 8))
        self._metric_table(parent, (("altitude", "Altitude", "ft"), ("pitch", "Pitch", "°"), ("roll", "Roll", "°"), ("gps", "GPS", "sats")))

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
