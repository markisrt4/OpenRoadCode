# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Vehicle-health dashboard for the orcUi vehicle screen."""

from __future__ import annotations

from ui.automotive.diagnostics_scan_if import DiagnosticsScanHandlerIf, DiagnosticsScanState

import tkinter as tk

from apps.orcUi.vehicle_presenter import VehiclePresentationState
from frontends.tk.automotive import DEFAULT_GAUGES
from frontends.tk.automotive.diagnostics_panel import VehicleDiagnosticsPanel
from frontends.tk.automotive.vehicle_gauge_theme import vehicle_gauge_theme_from_style_sheet
from frontends.tk.automotive.vehicle_gauge_widgets import LinearGauge
from ui.theme import ThemeBundle
from ui.ui_widget import UiWidget


class EnginePanel(tk.Frame, UiWidget):
    """Render live vehicle-health instrumentation."""

    _GAUGE_IDS = ("coolant", "intake", "load", "voltage")

    def __init__(
        self,
        parent: tk.Misc,
        *,
        theme: ThemeBundle,
        state: VehiclePresentationState,
        diagnostics_handler: DiagnosticsScanHandlerIf | None = None,
        diagnostics_state: DiagnosticsScanState = DiagnosticsScanState(),
    ) -> None:
        self._diagnostics_handler = diagnostics_handler
        self._diagnostics_state = diagnostics_state
        self._theme = theme
        self._state = state
        self._gauges: dict[str, LinearGauge] = {}
        super().__init__(parent, bg=theme.ui.background)
        self._build()
        self.update_state(state)
        self.update_diagnostics(diagnostics_state)

    def update_state(self, state: VehiclePresentationState) -> None:
        self._state = state
        values = {
            "coolant": state.coolant_temperature_f,
            "intake": state.intake_air_temperature_f,
            "load": state.engine_load_percent,
            "voltage": state.control_voltage_v,
        }
        for gauge_id, gauge in self._gauges.items():
            gauge.set_connected(True)
            gauge.set_value(values[gauge_id])

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
        tk.Frame(header, bg=ui.accent_warning, width=5).pack(side=tk.LEFT, fill=tk.Y)
        text = tk.Frame(header, bg=ui.surface_alt)
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=14, pady=7)
        tk.Label(
            text,
            text="HEALTH",
            fg=ui.text,
            bg=ui.surface_alt,
            font=("Sans", 16, "bold"),
            anchor="w",
        ).pack(anchor="w")
        tk.Label(
            text,
            text="Vehicle health and operating conditions",
            fg=ui.text_muted,
            bg=ui.surface_alt,
            font=("Sans", 11),
            anchor="w",
        ).pack(anchor="w")

        grid = tk.Frame(self, bg=ui.background)
        grid.grid(row=1, column=0, sticky="nsew")
        grid.grid_columnconfigure(0, weight=1)
        grid.grid_rowconfigure(1, weight=1)
        instruments = tk.Frame(grid, bg=ui.background)
        instruments.grid(row=0, column=0, sticky="ew")
        for column in range(4):
            instruments.grid_columnconfigure(column, weight=1, uniform="health-gauge")

        definitions = {
            definition.gauge_id: definition
            for definition in DEFAULT_GAUGES
            if definition.gauge_id in self._GAUGE_IDS
        }
        style = vehicle_gauge_theme_from_style_sheet(self._theme.style_sheet)

        for index, gauge_id in enumerate(self._GAUGE_IDS):
            definition = definitions[gauge_id]
            row, column = 0, index
            card = self._instrument_card(
                instruments,
                title=definition.title.upper(),
                unit=definition.unit,
            )
            card.grid(row=row, column=column, sticky="nsew", padx=4, pady=4)
            card.grid_columnconfigure(0, weight=1)
            card.grid_rowconfigure(1, weight=1)

            gauge = LinearGauge(
                card,
                title="",
                unit=definition.unit,
                minimum=definition.minimum,
                maximum=definition.maximum,
                caution_low=definition.caution_low,
                danger_low=definition.danger_low,
                caution_high=definition.caution_high,
                danger_high=definition.danger_high,
                icon=definition.icon,
                precision=definition.precision,
                style=style,
                width=150,
                height=82,
            )
            gauge.grid(row=1, column=0, sticky="nsew", padx=5, pady=(0, 5))
            self._gauges[gauge_id] = gauge

        self._diagnostics_panel = VehicleDiagnosticsPanel(
            grid, theme=self._theme, handler=self._diagnostics_handler,
        )
        self._diagnostics_panel.grid(row=1, column=0, sticky="nsew", padx=4, pady=4)

    def update_diagnostics(self, state: DiagnosticsScanState) -> None:
        self._diagnostics_state = state
        self._diagnostics_panel.update_diagnostics(state)

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
