# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Vehicle-health dashboard for the orcUi vehicle screen."""

from __future__ import annotations

from ui.automotive.diagnostics_scan_if import DiagnosticsScanHandlerIf, DiagnosticsScanState

import tkinter as tk

from apps.orcUi.vehicle_presenter import VehiclePresentationState
from frontends.tk.automotive import DEFAULT_GAUGES
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
        grid.grid_columnconfigure(0, weight=1, uniform="engine")
        grid.grid_columnconfigure(1, weight=1, uniform="engine")
        for row in range(3):
            grid.grid_rowconfigure(row, weight=1)

        definitions = {
            definition.gauge_id: definition
            for definition in DEFAULT_GAUGES
            if definition.gauge_id in self._GAUGE_IDS
        }
        style = vehicle_gauge_theme_from_style_sheet(self._theme.style_sheet)

        for index, gauge_id in enumerate(self._GAUGE_IDS):
            definition = definitions[gauge_id]
            row, column = divmod(index, 2)
            card = self._instrument_card(
                grid,
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
                width=260,
                height=82,
            )
            gauge.grid(row=1, column=0, sticky="nsew", padx=5, pady=(0, 5))
            self._gauges[gauge_id] = gauge

        summary = tk.Frame(
            grid,
            bg=ui.surface_alt,
            highlightthickness=1,
            highlightbackground=ui.border,
        )
        summary.grid(row=2, column=1, sticky="nsew", padx=4, pady=4)
        tk.Label(
            summary,
            text="HEALTH STATUS",
            fg=ui.text_muted,
            bg=ui.surface_alt,
            font=("Sans", 10, "bold"),
        ).pack(anchor="w", padx=12, pady=(12, 4))
        self._scan_button = tk.Button(
            summary, text="Scan Now", command=self._request_scan,
            bg=ui.control_background, fg=ui.control_text,
        )
        self._scan_button.pack(anchor="w", padx=12)
        self._diagnostics_summary = tk.Label(summary, bg=ui.surface_alt, fg=ui.text,
                                             anchor="w", justify=tk.LEFT, wraplength=420)
        self._diagnostics_summary.pack(fill=tk.X, padx=12, pady=4)
        self._diagnostics_details = tk.Text(summary, height=8, width=46, wrap=tk.WORD,
                                          bg=ui.surface_alt, fg=ui.text, relief=tk.FLAT)
        self._diagnostics_details.pack(fill=tk.BOTH, expand=True, padx=12, pady=4)

    def _request_scan(self) -> None:
        if self._diagnostics_handler is not None:
            self._diagnostics_handler.request_scan()

    def update_diagnostics(self, state: DiagnosticsScanState) -> None:
        self._diagnostics_state = state
        self._scan_button.configure(
            text="Scanning…" if state.scanning else "Scan Now",
            state=tk.DISABLED if state.scanning or self._diagnostics_handler is None else tk.NORMAL,
        )
        self._diagnostics_summary.configure(text=f"{state.status.upper()}: {state.summary}")
        self._diagnostics_details.configure(state=tk.NORMAL)
        self._diagnostics_details.delete("1.0", tk.END)
        self._diagnostics_details.insert("1.0", state.details)
        self._diagnostics_details.configure(state=tk.DISABLED)

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
