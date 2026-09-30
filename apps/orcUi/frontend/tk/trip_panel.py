# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Trip-computer presentation for the orcUi vehicle screen."""

from __future__ import annotations

import tkinter as tk

from apps.orcUi.trip_presenter import TripPresentationState
from controllers.automotive import VehicleConfiguration
from frontends.tk.automotive.trip_metric_card import TripMetricCard
from ui.theme import ThemeBundle
from .shell_metrics import FONT_BODY, FONT_CONTROL, FONT_SMALL


class TripPanel(tk.Frame):
    """Render and update trip telemetry independently of VehiclePanel."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        theme: ThemeBundle,
        vehicle_configuration: VehicleConfiguration,
        state: TripPresentationState,
    ) -> None:
        self._theme = theme
        self._vehicle_configuration = vehicle_configuration
        self._state = state
        self._cards: dict[str, TripMetricCard] = {}
        self._boost_labels: dict[str, tk.Label] = {}
        super().__init__(parent, bg=theme.ui.background)
        self._build()
        self.update_state(state)

    def update_state(self, state: TripPresentationState) -> None:
        self._state = state
        values = {
            "distance": f"{state.distance_miles:.1f}",
            "elapsed": self._format_duration(state.elapsed_s),
            "moving": self._format_duration(state.moving_s),
            "stopped": self._format_duration(state.stopped_s),
            "average": "--" if state.average_speed_mph is None else f"{state.average_speed_mph:.1f}",
            "maximum": "--" if state.maximum_speed_mph is None else f"{state.maximum_speed_mph:.1f}",
            "fuel_used": "--" if state.fuel_used_gallons is None else f"{state.fuel_used_gallons:.2f}",
            "economy": "--" if state.economy_mpg is None else f"{state.economy_mpg:.1f}",
            "status": state.status.upper(),
        }
        status_colors = {
            "active": self._theme.ui.accent_success,
            "paused": self._theme.ui.accent_warning,
            "complete": self._theme.ui.accent_primary,
            "idle": self._theme.ui.text_muted,
        }
        for key, text in values.items():
            card = self._cards.get(key)
            if card is not None:
                card.set_value(
                    text,
                    accent=status_colors.get(state.status)
                    if key == "status"
                    else None,
                )

        boost_values = {
            "boost_time": self._format_duration(state.boost_time_s),
            "boost_distance": f"{state.boost_distance_miles:.1f}",
            "boost_fuel": f"{state.boost_fuel_gallons:.2f}",
            "boost_share": "--" if state.boost_fuel_percent is None else f"{state.boost_fuel_percent:.0f}",
            "peak_boost": "--" if state.peak_boost_psi is None else f"{state.peak_boost_psi:.1f}",
            "high_load_fuel": f"{state.high_load_fuel_gallons:.2f}",
            "high_load_share": "--" if state.high_load_fuel_percent is None else f"{state.high_load_fuel_percent:.0f}",
        }
        for key, text in boost_values.items():
            label = self._boost_labels.get(key)
            if label is not None:
                label.configure(text=text)

    def _build(self) -> None:
        ui = self._theme.ui
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = tk.Frame(
            self,
            bg=ui.surface_alt,
            highlightthickness=1,
            highlightbackground=ui.border,
        )
        header.grid(row=0, column=0, sticky="ew", padx=2, pady=(2, 6))
        header.grid_columnconfigure(1, weight=1)

        road = tk.Canvas(
            header,
            width=70,
            height=58,
            bg=ui.surface_alt,
            highlightthickness=0,
            bd=0,
        )
        road.grid(row=0, column=0, rowspan=2, padx=(16, 10), pady=7)
        road.create_polygon(
            10, 54, 28, 7, 42, 7, 60, 54,
            fill=ui.accent_primary,
            outline="",
        )
        road.create_line(35, 49, 35, 37, fill=ui.surface_alt, width=4)
        road.create_line(35, 30, 35, 21, fill=ui.surface_alt, width=3)
        road.create_line(35, 15, 35, 11, fill=ui.surface_alt, width=2)

        tk.Label(
            header,
            text="TRIP COMPUTER",
            fg=ui.text,
            bg=ui.surface_alt,
            font=("Sans", 18, "bold"),
            anchor="w",
        ).grid(row=0, column=1, sticky="sw", pady=(8, 0))
        tk.Label(
            header,
            text="Track your journey. Know your drive.",
            fg=ui.text_muted,
            bg=ui.surface_alt,
            font=("Sans", FONT_SMALL),
            anchor="w",
        ).grid(row=1, column=1, sticky="nw", pady=(0, 8))

        grid = tk.Frame(self, bg=ui.background)
        grid.grid(row=1, column=0, sticky="nsew")
        for column in range(3):
            grid.grid_columnconfigure(column, weight=1, uniform="trip")
        for row in range(3):
            grid.grid_rowconfigure(row, weight=1, uniform="trip")

        metrics = (
            ("status", "TRIP STATUS", "", "status", ui.accent_success),
            ("distance", "DISTANCE", "mi", "pin", ui.accent_primary),
            ("elapsed", "ELAPSED TIME", "", "clock", ui.accent_primary),
            ("moving", "MOVING TIME", "", "wheel", ui.accent_success),
            ("stopped", "STOPPED TIME", "", "pause", ui.accent_danger),
            ("average", "AVERAGE SPEED", "MPH", "speed", ui.accent_warning),
            ("maximum", "MAXIMUM SPEED", "MPH", "speed", ui.accent_warning),
            ("fuel_used", "FUEL USED", "gal", "fuel", ui.text_muted),
            ("economy", "FUEL ECONOMY", "MPG", "chart", ui.text_muted),
        )
        for index, (key, title, unit, icon, accent) in enumerate(metrics):
            row, column = divmod(index, 3)
            card = TripMetricCard(
                grid,
                title=title,
                unit=unit,
                icon=icon,
                background=ui.surface,
                border=ui.border,
                text=ui.text,
                muted=ui.text_muted,
                accent=accent,
            )
            card.grid(row=row, column=column, sticky="nsew", padx=4, pady=4)
            self._cards[key] = card

        if self._vehicle_configuration.induction.is_forced_induction:
            self._build_boost_band()

    def _build_boost_band(self) -> None:
        ui = self._theme.ui
        boost_band = tk.Frame(
            self,
            bg=ui.surface_alt,
            highlightthickness=1,
            highlightbackground=ui.border,
        )
        boost_band.grid(row=2, column=0, sticky="ew", padx=4, pady=(6, 2))
        tk.Label(
            boost_band,
            text="BOOST / LOAD METRICS",
            fg=ui.text_muted,
            bg=ui.surface_alt,
            font=("Sans", FONT_SMALL, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=(12, 8), pady=9)

        boost_specs = (
            ("boost_time", "TIME", ""),
            ("boost_distance", "DIST", "mi"),
            ("boost_fuel", "FUEL", "gal"),
            ("boost_share", "FUEL SHARE", "%"),
            ("peak_boost", "PEAK", "psi"),
            ("high_load_fuel", "LOAD FUEL", "gal"),
            ("high_load_share", "LOAD SHARE", "%"),
        )
        for column, (key, title, unit) in enumerate(boost_specs, start=1):
            cell = tk.Frame(boost_band, bg=ui.surface_alt)
            cell.grid(row=0, column=column, sticky="ew", padx=8, pady=5)
            boost_band.grid_columnconfigure(column, weight=1)
            tk.Label(
                cell,
                text=title,
                fg=ui.text_muted,
                bg=ui.surface_alt,
                font=("Sans", FONT_SMALL, "bold"),
            ).pack()
            value = tk.Label(
                cell,
                text="--",
                fg=ui.text,
                bg=ui.surface_alt,
                font=("Sans", FONT_BODY, "bold"),
            )
            value.pack()
            if unit:
                tk.Label(
                    cell,
                    text=unit,
                    fg=ui.text_muted,
                    bg=ui.surface_alt,
                    font=("Sans", FONT_SMALL),
                ).pack()
            self._boost_labels[key] = value

    @staticmethod
    def _format_duration(seconds: float) -> str:
        total = max(0, round(seconds))
        hours, remainder = divmod(total, 3600)
        minutes, secs = divmod(remainder, 60)
        return f"{hours:d}:{minutes:02d}:{secs:02d}"
