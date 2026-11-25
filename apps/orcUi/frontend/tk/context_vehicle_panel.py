# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Vehicle gauge construction and updates for the Home context rail."""

from __future__ import annotations

import tkinter as tk

from frontends.tk.automotive import FuelLevelGauge
from frontends.tk.automotive.vehicle_gauge_theme import vehicle_gauge_theme_from_style_sheet
from frontends.tk.automotive.vehicle_gauge_widgets import LinearGauge, RoundGauge

from .shell_metrics import FONT_CONTROL, FONT_SMALL


class ContextVehiclePanel:
    """Vehicle gauge helpers shared with the context rail."""

    def _build_vehicle(self, parent: tk.Frame) -> None:
        ui = self._theme.ui
        gauge_style = vehicle_gauge_theme_from_style_sheet(self._theme.style_sheet)
        cluster = tk.Frame(parent, bg=ui.surface)
        cluster.pack(fill=tk.BOTH, expand=True)
        cluster.grid_columnconfigure(0, weight=1)
        cluster.grid_columnconfigure(1, weight=1)
        cluster.grid_rowconfigure(0, weight=3)
        cluster.grid_rowconfigure(1, weight=3)
        cluster.grid_rowconfigure(2, weight=1)

        rpm_cell = self._compact_gauge_cell(cluster, "RPM", "×1000", 0, 0, (0, 2), (0, 2))
        rpm = RoundGauge(
            rpm_cell,
            title="",
            unit="",
            minimum=0.0,
            maximum=8.0,
            major_step=1.0,
            caution_start=6.0,
            danger_start=6.8,
            precision=1,
            style=gauge_style,
            size=112,
        )
        rpm.pack(fill=tk.BOTH, expand=True)

        speed_cell = self._compact_gauge_cell(cluster, "SPEED", "MPH", 0, 1, (2, 0), (0, 2))
        speed = RoundGauge(
            speed_cell,
            title="",
            unit="",
            minimum=0.0,
            maximum=160.0,
            major_step=40.0,
            precision=0,
            style=gauge_style,
            size=112,
        )
        speed.pack(fill=tk.BOTH, expand=True)

        boost_cell = self._compact_gauge_cell(cluster, "BOOST", "PSI", 1, 0, (0, 2), 2)
        boost = RoundGauge(
            boost_cell,
            title="",
            unit="",
            minimum=-15.0,
            maximum=25.0,
            major_step=5.0,
            caution_start=18.0,
            danger_start=22.0,
            precision=1,
            style=gauge_style,
            size=112,
        )
        boost.pack(fill=tk.BOTH, expand=True)

        fuel_cell = self._compact_gauge_cell(cluster, "FUEL", "%", 1, 1, (2, 0), 2)
        fuel = FuelLevelGauge(fuel_cell, style=gauge_style, size=112, show_title=False)
        fuel.pack(fill=tk.BOTH, expand=True)

        status = tk.Frame(cluster, bg=ui.surface)
        status.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=(2, 0))
        status.grid_columnconfigure(0, weight=1)
        coolant = LinearGauge(
            status,
            title="Coolant",
            unit="°F",
            minimum=100.0,
            maximum=260.0,
            caution_high=225.0,
            danger_high=240.0,
            icon="coolant",
            normal_segment_color="#36b8f5",
            precision=0,
            style=gauge_style,
            width=190,
            height=58,
        )
        coolant.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        gear = self._card(status)
        gear.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
        tk.Label(
            gear, text="GEAR", fg=ui.text_muted, bg=ui.surface, font=("Sans", FONT_SMALL, "bold")
        ).pack(padx=10, pady=(4, 0))
        self._gear_value_label = tk.Label(
            gear,
            text="—",
            fg=ui.accent_danger,
            bg=ui.surface,
            font=("Sans", 22, "bold"),
        )
        self._gear_value_label.pack(padx=10, pady=(0, 3))
        self._vehicle_gauges.update(rpm=rpm, speed=speed, boost=boost, fuel=fuel, coolant=coolant)
        self._paint_vehicle_values()

    def _compact_gauge_cell(
        self,
        parent: tk.Frame,
        title: str,
        unit: str,
        row: int,
        column: int,
        padx: tuple[int, int] | int,
        pady: tuple[int, int] | int,
    ) -> tk.Frame:
        ui = self._theme.ui
        cell = tk.Frame(parent, bg=ui.surface)
        cell.grid(row=row, column=column, sticky="nsew", padx=padx, pady=pady)
        label = tk.Frame(cell, bg=ui.surface)
        label.pack(side=tk.BOTTOM, fill=tk.X, pady=(0, 1))
        tk.Label(
            label, text=title, fg=ui.text, bg=ui.surface, font=("Sans", FONT_CONTROL, "bold")
        ).pack(side=tk.LEFT, expand=True, anchor="e")
        tk.Label(label, text=unit, fg=ui.text_muted, bg=ui.surface, font=("Sans", FONT_SMALL)).pack(
            side=tk.LEFT, expand=True, anchor="w", padx=(4, 0)
        )
        return cell

    def _paint_vehicle_values(self) -> None:
        state = self._vehicle_state
        values = {
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

    def _card(self, parent: tk.Misc) -> tk.Frame:
        ui = self._theme.ui
        return tk.Frame(
            parent,
            bg=ui.surface,
            highlightthickness=1,
            highlightcolor=ui.border,
            highlightbackground=ui.border,
        )
