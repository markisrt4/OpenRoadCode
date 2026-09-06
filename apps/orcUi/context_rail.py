# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Switchable secondary context rail for the ORC cockpit home screen."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from dataclasses import dataclass

from apps.orcUi.navigation_presenter import AttitudePresentationState, PositionPresentationState
from apps.orcUi.theme_runtime import theme_bundle as packaged_theme_bundle
from apps.orcUi.vehicle_presenter import VehiclePresentationState
from frontends.tk.automotive import FuelLevelGauge
from frontends.tk.automotive.vehicle_gauge_theme import vehicle_gauge_theme_from_style_sheet
from frontends.tk.automotive.vehicle_gauge_widgets import LinearGauge, RoundGauge
from ui.theme import ThemeBundle, ThemeMode


@dataclass(frozen=True)
class ContextPage:
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
        *,
        theme: ThemeBundle | None = None,
    ) -> None:
        self._theme = theme or packaged_theme_bundle(ThemeMode.DARK)
        ui = self._theme.ui
        super().__init__(
            parent,
            bg=ui.surface,
            width=self.WIDTH,
            highlightthickness=1,
            highlightbackground=ui.border,
        )
        self.pack_propagate(False)
        self._on_expand = on_expand
        self._vehicle_state = VehiclePresentationState()
        self._position_state = PositionPresentationState()
        self._attitude_state = AttitudePresentationState()
        self._vehicle_gauges: dict[str, RoundGauge | LinearGauge | FuelLevelGauge] = {}
        self._gear_value_label: tk.Label | None = None
        self._offroad_value_labels: dict[str, tk.Label] = {}
        self._page_index = 0
        self._title: tk.Label
        self._body: tk.Frame
        self._rebuild()

    @property
    def selected_page(self) -> str:
        return self._pages()[self._page_index].name

    def set_theme_bundle(self, theme: ThemeBundle) -> None:
        """Apply a CSS-derived theme while preserving page and telemetry state."""
        self._theme = theme
        self.configure(bg=theme.ui.surface, highlightbackground=theme.ui.border)
        self._rebuild()

    def update_vehicle_state(self, state: VehiclePresentationState) -> None:
        self._vehicle_state = state
        if self.selected_page == "VEHICLE":
            self._paint_vehicle_values()
        elif self.selected_page == "OFF-ROAD":
            self._paint_offroad_values()

    def update_position_state(self, state: PositionPresentationState) -> None:
        self._position_state = state
        if self.selected_page == "OFF-ROAD":
            self._paint_offroad_values()

    def update_attitude_state(self, state: AttitudePresentationState) -> None:
        self._attitude_state = state
        if self.selected_page == "OFF-ROAD":
            self._paint_offroad_values()

    def _pages(self) -> tuple[ContextPage, ...]:
        ui = self._theme.ui
        return (
            ContextPage("VEHICLE", ui.accent_success, self._build_vehicle),
            ContextPage("TRIP", ui.accent_primary, self._build_trip),
            ContextPage("OFF-ROAD", ui.accent_warning, self._build_offroad),
        )

    def _rebuild(self) -> None:
        for child in self.winfo_children():
            child.destroy()
        self._vehicle_gauges.clear()
        self._gear_value_label = None
        self._offroad_value_labels.clear()
        self._build_header()
        self._body = tk.Frame(self, bg=self._theme.ui.surface)
        self._body.pack(fill=tk.BOTH, expand=True, padx=10, pady=(2, 10))
        self._show_page()

    def _build_header(self) -> None:
        ui = self._theme.ui
        header = tk.Frame(self, bg=ui.surface)
        header.pack(fill=tk.X, padx=8, pady=(7, 3))
        header.grid_columnconfigure(1, weight=1)
        self._title = tk.Label(header, text="", bg=ui.surface, font=("Sans", 10, "bold"))
        self._nav_button(header, "‹", self._previous_page).grid(row=0, column=0, sticky="w")
        self._title.grid(row=0, column=1)
        controls = tk.Frame(header, bg=ui.surface)
        controls.grid(row=0, column=2, sticky="e")
        if self._on_expand is not None:
            self._nav_button(controls, "□", self._expand_page, width=2, font_size=12).pack(side=tk.LEFT)
        self._nav_button(controls, "›", self._next_page).pack(side=tk.LEFT)

    def _nav_button(
        self,
        parent: tk.Misc,
        text: str,
        command: Callable[[], None],
        *,
        width: int = 3,
        font_size: int = 16,
    ) -> tk.Button:
        ui = self._theme.ui
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=ui.control_background,
            fg=ui.control_text,
            activebackground=ui.control_active,
            activeforeground="#ffffff",
            relief=tk.FLAT,
            bd=0,
            width=width,
            font=("Sans", font_size, "bold"),
            cursor="hand2",
        )

    def _expand_page(self) -> None:
        if self._on_expand is not None:
            self._on_expand(self.selected_page)

    def _previous_page(self) -> None:
        pages = self._pages()
        self._page_index = (self._page_index - 1) % len(pages)
        self._show_page()

    def _next_page(self) -> None:
        pages = self._pages()
        self._page_index = (self._page_index + 1) % len(pages)
        self._show_page()

    def _show_page(self) -> None:
        ui = self._theme.ui
        for child in self._body.winfo_children():
            child.destroy()
        self._vehicle_gauges.clear()
        self._gear_value_label = None
        self._offroad_value_labels.clear()
        pages = self._pages()
        page = pages[self._page_index]
        self._title.configure(text=page.name, fg=page.accent, bg=ui.surface)
        page.builder(self._body)
        dots = tk.Frame(self._body, bg=ui.surface)
        dots.pack(side=tk.BOTTOM, pady=(4, 0))
        for index in range(len(pages)):
            tk.Label(
                dots,
                text="●" if index == self._page_index else "·",
                fg=page.accent if index == self._page_index else ui.text_muted,
                bg=ui.surface,
                font=("Sans", 9),
            ).pack(side=tk.LEFT, padx=2)

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

        rpm_cell = self._compact_gauge_cell(cluster, "RPM", "×1000", row=0, column=0, padx=(0, 2), pady=(0, 2))
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

        speed_cell = self._compact_gauge_cell(cluster, "SPEED", "MPH", row=0, column=1, padx=(2, 0), pady=(0, 2))
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

        boost_cell = self._compact_gauge_cell(cluster, "BOOST", "PSI", row=1, column=0, padx=(0, 2), pady=2)
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

        fuel_cell = self._compact_gauge_cell(cluster, "FUEL", "%", row=1, column=1, padx=(2, 0), pady=2)
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
            precision=0,
            style=gauge_style,
            width=190,
            height=58,
        )
        coolant.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        gear = tk.Frame(
            status,
            bg=ui.surface,
            highlightthickness=1,
            highlightbackground=ui.border,
        )
        gear.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
        tk.Label(
            gear,
            text="GEAR",
            fg=ui.text_muted,
            bg=ui.surface,
            font=("Sans", 7, "bold"),
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
        *,
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
            label,
            text=title,
            fg=ui.text,
            bg=ui.surface,
            font=("Sans", 8, "bold"),
        ).pack(side=tk.LEFT, expand=True, anchor="e")
        tk.Label(
            label,
            text=unit,
            fg=ui.text_muted,
            bg=ui.surface,
            font=("Sans", 7),
        ).pack(side=tk.LEFT, expand=True, anchor="w", padx=(4, 0))
        return cell

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
        self._metric_table(
            parent,
            (
                ("distance", "Distance", "mi"),
                ("elapsed", "Elapsed", ""),
                ("average", "Avg speed", "MPH"),
                ("moving", "Moving", ""),
                ("fuel_used", "Fuel used", "gal"),
                ("economy", "Economy", "MPG"),
            ),
        )

    def _build_offroad(self, parent: tk.Frame) -> None:
        ui = self._theme.ui
        panel = tk.Frame(parent, bg=ui.surface)
        panel.pack(fill=tk.BOTH, expand=True)
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_columnconfigure(1, weight=1)

        status = self._card(panel)
        status.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(2, 6))
        status.grid_columnconfigure(1, weight=1)
        tk.Label(status, text="GPS", fg=ui.text_muted, bg=ui.surface, font=("Sans", 8, "bold")).grid(
            row=0, column=0, padx=(8, 4), pady=5
        )
        self._offroad_value_labels["fix"] = tk.Label(
            status,
            text="NO FIX",
            fg=ui.accent_danger,
            bg=ui.surface,
            font=("Sans", 10, "bold"),
        )
        self._offroad_value_labels["fix"].grid(row=0, column=1, sticky="w", pady=5)
        self._offroad_value_labels["accuracy"] = tk.Label(
            status,
            text="± -- m",
            fg=ui.text_muted,
            bg=ui.surface,
            font=("Sans", 9, "bold"),
        )
        self._offroad_value_labels["accuracy"].grid(row=0, column=2, padx=(4, 8), pady=5)

        heading = self._card(panel)
        heading.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(0, 6))
        tk.Label(
            heading,
            text="HEADING",
            fg=ui.accent_warning,
            bg=ui.surface,
            font=("Sans", 7, "bold"),
        ).pack(pady=(5, 0))
        self._offroad_value_labels["heading"] = tk.Label(
            heading,
            text="--",
            fg=ui.text,
            bg=ui.surface,
            font=("Sans", 22, "bold"),
        )
        self._offroad_value_labels["heading"].pack(pady=(0, 5))

        self._offroad_metric_card(panel, "PITCH", "pitch", "°").grid(
            row=2, column=0, sticky="nsew", padx=(0, 3), pady=(0, 6)
        )
        self._offroad_metric_card(panel, "ROLL", "roll", "°").grid(
            row=2, column=1, sticky="nsew", padx=(3, 0), pady=(0, 6)
        )
        self._offroad_metric_card(panel, "ALTITUDE", "altitude", "ft").grid(
            row=3, column=0, sticky="nsew", padx=(0, 3), pady=(0, 6)
        )
        self._offroad_metric_card(panel, "SPEED", "speed", "mph").grid(
            row=3, column=1, sticky="nsew", padx=(3, 0), pady=(0, 6)
        )

        footer = self._card(panel)
        footer.grid(row=4, column=0, columnspan=2, sticky="ew")
        footer.grid_columnconfigure(0, weight=1)
        self._offroad_value_labels["coordinates"] = tk.Label(
            footer,
            text="--",
            fg=ui.text,
            bg=ui.surface,
            font=("Monospace", 8, "bold"),
            anchor="w",
        )
        self._offroad_value_labels["coordinates"].grid(row=0, column=0, sticky="ew", padx=(8, 4), pady=6)
        self._offroad_value_labels["satellites"] = tk.Label(
            footer,
            text="-- sat",
            fg=ui.text_muted,
            bg=ui.surface,
            font=("Sans", 8, "bold"),
        )
        self._offroad_value_labels["satellites"].grid(row=0, column=1, sticky="e", padx=(4, 8), pady=6)
        self._paint_offroad_values()

    def _card(self, parent: tk.Misc) -> tk.Frame:
        ui = self._theme.ui
        return tk.Frame(
            parent,
            bg=ui.surface,
            highlightthickness=1,
            highlightbackground=ui.border,
        )

    def _offroad_metric_card(self, parent: tk.Misc, title: str, key: str, unit: str) -> tk.Frame:
        ui = self._theme.ui
        card = self._card(parent)
        tk.Label(card, text=title, fg=ui.text_muted, bg=ui.surface, font=("Sans", 7, "bold")).pack(pady=(5, 0))
        value_row = tk.Frame(card, bg=ui.surface)
        value_row.pack(pady=(0, 5))
        value = tk.Label(value_row, text="--", fg=ui.text, bg=ui.surface, font=("Sans", 15, "bold"))
        value.pack(side=tk.LEFT)
        tk.Label(value_row, text=unit, fg=ui.text_muted, bg=ui.surface, font=("Sans", 7)).pack(
            side=tk.LEFT, padx=(3, 0), pady=(6, 0)
        )
        self._offroad_value_labels[key] = value
        return card

    def _paint_offroad_values(self) -> None:
        ui = self._theme.ui
        position = self._position_state
        attitude = self._attitude_state
        vehicle = self._vehicle_state
        heading = attitude.heading_deg
        heading_text = "--" if heading is None else f"{self._cardinal_direction(heading)}  {heading:03.0f}°"
        coordinates = (
            "--"
            if position.latitude_deg is None or position.longitude_deg is None
            else f"{position.latitude_deg:.5f}°  {position.longitude_deg:.5f}°"
        )
        values = {
            "heading": heading_text,
            "pitch": self._signed(attitude.pitch_deg),
            "roll": self._signed(attitude.roll_deg),
            "altitude": self._format(position.altitude_ft, ".0f"),
            "speed": self._format(vehicle.speed_mph, ".0f"),
            "fix": self._fix_text(position.fix_mode),
            "accuracy": "± -- m" if position.accuracy_m is None else f"± {position.accuracy_m:.1f} m",
            "coordinates": coordinates,
            "satellites": "-- sat" if position.satellites_used is None else f"{position.satellites_used} sat",
        }
        for key, value in values.items():
            label = self._offroad_value_labels.get(key)
            if label is not None:
                label.configure(text=value)

        fix_label = self._offroad_value_labels.get("fix")
        if fix_label is not None:
            fix_label.configure(fg=self._fix_color(position.fix_mode))

        for key, value in (("pitch", attitude.pitch_deg), ("roll", attitude.roll_deg)):
            label = self._offroad_value_labels.get(key)
            if label is not None:
                label.configure(
                    fg=ui.accent_danger if value is not None and abs(value) >= 20.0 else ui.text
                )

    @staticmethod
    def _fix_text(fix_mode: int | None) -> str:
        return {1: "NO FIX", 2: "2D FIX", 3: "3D FIX"}.get(fix_mode, "NO FIX")

    def _fix_color(self, fix_mode: int | None) -> str:
        ui = self._theme.ui
        if fix_mode is not None and fix_mode >= 3:
            return ui.accent_success
        if fix_mode == 2:
            return ui.accent_warning
        return ui.accent_danger

    @staticmethod
    def _cardinal_direction(heading_deg: float) -> str:
        directions = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")
        index = int((heading_deg % 360.0 + 22.5) // 45.0) % len(directions)
        return directions[index]

    @staticmethod
    def _signed(value: float | None) -> str:
        return "--" if value is None else f"{value:+.1f}"

    @staticmethod
    def _format(value: float | None, spec: str) -> str:
        return "--" if value is None else format(value, spec)

    def _metric_table(
        self,
        parent: tk.Frame,
        metrics: tuple[tuple[str, str, str], ...],
        value_labels: dict[str, tk.Label] | None = None,
    ) -> None:
        ui = self._theme.ui
        grid = tk.Frame(parent, bg=ui.surface)
        grid.pack(fill=tk.BOTH, expand=True)
        grid.grid_columnconfigure(0, weight=2)
        grid.grid_columnconfigure(1, weight=1)
        grid.grid_columnconfigure(2, weight=1)
        for row, (key, label, unit) in enumerate(metrics):
            tk.Label(
                grid,
                text=label,
                fg=ui.text_muted,
                bg=ui.surface,
                font=("Sans", 9),
                anchor="w",
            ).grid(row=row, column=0, sticky="w", padx=(2, 4), pady=3)
            value = tk.Label(
                grid,
                text="--",
                fg=ui.text,
                bg=ui.surface,
                font=("Sans", 12, "bold"),
                anchor="e",
            )
            value.grid(row=row, column=1, sticky="e", padx=4, pady=3)
            if value_labels is not None:
                value_labels[key] = value
            tk.Label(
                grid,
                text=unit,
                fg=ui.text_muted,
                bg=ui.surface,
                font=("Sans", 8),
                anchor="w",
            ).grid(row=row, column=2, sticky="w", padx=(0, 2), pady=3)
