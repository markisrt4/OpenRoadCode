# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Performance dashboard for the orcUi vehicle screen."""

from __future__ import annotations

import tkinter as tk

from apps.orcUi.vehicle_presenter import VehiclePresentationState
from controllers.automotive import VehicleConfiguration
from frontends.tk.automotive import DEFAULT_GAUGES, ShifterGauge
from frontends.tk.automotive.vehicle_gauge_theme import vehicle_gauge_theme_from_style_sheet
from frontends.tk.automotive.vehicle_gauge_widgets import RoundGauge
from ui.theme import ThemeBundle


class PerformancePanel(tk.Frame):
    """Render the primary live-driving gauges and gear indicator."""

    _GAUGE_IDS = ("rpm", "boost", "speed", "throttle")

    def __init__(
        self,
        parent: tk.Misc,
        *,
        theme: ThemeBundle,
        vehicle_configuration: VehicleConfiguration,
        state: VehiclePresentationState,
    ) -> None:
        self._theme = theme
        self._vehicle_configuration = vehicle_configuration
        self._state = state
        self._gauges: dict[str, RoundGauge] = {}
        self._shifter: ShifterGauge | None = None
        super().__init__(parent, bg=theme.ui.background)
        self._build()
        self.update_state(state)

    def update_state(self, state: VehiclePresentationState) -> None:
        self._state = state
        values = {
            "rpm": None if state.engine_speed_rpm is None else state.engine_speed_rpm / 1000.0,
            "boost": state.boost_psi,
            "speed": state.speed_mph,
            "throttle": state.throttle_percent,
        }
        for gauge_id, gauge in self._gauges.items():
            gauge.set_connected(True)
            gauge.set_value(values[gauge_id])
        if self._shifter is not None:
            self._shifter.set_gear(state.gear)

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
        header.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        tk.Frame(header, bg=ui.accent_danger, width=5).pack(side=tk.LEFT, fill=tk.Y)
        text = tk.Frame(header, bg=ui.surface_alt)
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=14, pady=7)
        tk.Label(
            text,
            text="PERFORMANCE",
            fg=ui.text,
            bg=ui.surface_alt,
            font=("Sans", 16, "bold"),
            anchor="w",
        ).pack(anchor="w")
        tk.Label(
            text,
            text="Live driving dynamics",
            fg=ui.text_muted,
            bg=ui.surface_alt,
            font=("Sans", 11),
            anchor="w",
        ).pack(anchor="w")

        cluster = tk.Frame(self, bg=ui.background)
        cluster.grid(row=1, column=0, sticky="nsew")
        cluster.grid_rowconfigure(0, weight=1)
        for column in range(4):
            cluster.grid_columnconfigure(column, weight=1, uniform="performance")

        definitions = {
            definition.gauge_id: definition
            for definition in DEFAULT_GAUGES
            if definition.gauge_id in self._GAUGE_IDS
        }
        gauge_style = vehicle_gauge_theme_from_style_sheet(self._theme.style_sheet)

        for column, gauge_id in enumerate(self._GAUGE_IDS):
            definition = definitions[gauge_id]
            title = definition.title.upper()
            if (
                gauge_id == "boost"
                and not self._vehicle_configuration.induction.is_forced_induction
            ):
                title = "MANIFOLD"

            card = self._instrument_card(
                cluster,
                title=title,
                unit=definition.unit,
            )
            card.grid(row=0, column=column, sticky="nsew", padx=4, pady=2)
            card.grid_columnconfigure(0, weight=1)
            card.grid_rowconfigure(1, weight=1)

            gauge = RoundGauge(
                card,
                title="",
                unit=definition.unit,
                minimum=definition.minimum,
                maximum=definition.maximum,
                major_step=definition.major_step,
                caution_start=definition.caution_high,
                danger_start=definition.danger_high,
                intense_redline=definition.intense_redline,
                redline_style=definition.redline_style,
                start_angle=definition.start_angle,
                sweep_angle=definition.sweep_angle,
                precision=definition.precision,
                style=gauge_style,
                size=205,
            )
            gauge.grid(row=1, column=0, sticky="nsew", padx=2, pady=(0, 2))
            self._gauges[gauge_id] = gauge

        lower = tk.Frame(self, bg=ui.background)
        lower.grid(row=2, column=0, sticky="ew", pady=(5, 0))
        lower.grid_columnconfigure(0, weight=1)
        self._shifter = ShifterGauge(lower, width=280, height=58)
        self._shifter.set_style_sheet(self._theme.style_sheet)
        self._shifter.grid(row=0, column=0)

    def _instrument_card(
        self,
        parent: tk.Misc,
        *,
        title: str,
        unit: str,
    ) -> tk.Frame:
        ui = self._theme.ui
        card = tk.Frame(
            parent,
            bg=ui.surface,
            highlightthickness=1,
            highlightbackground=ui.border,
        )
        top = tk.Frame(card, bg=ui.surface)
        top.grid(row=0, column=0, sticky="ew", padx=10, pady=(7, 2))
        top.grid_columnconfigure(1, weight=1)
        tk.Label(
            top,
            text=title,
            fg=ui.text,
            bg=ui.surface,
            font=("Sans", 11, "bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w")
        if unit:
            tk.Label(
                top,
                text=unit,
                fg=ui.text_muted,
                bg=ui.surface,
                font=("Sans", 9, "bold"),
            ).grid(row=0, column=1, sticky="e")
        return card
