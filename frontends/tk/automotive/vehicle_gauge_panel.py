# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Configurable OpenRoadCode vehicle gauge panel."""

from __future__ import annotations

import json
import tkinter as tk
from collections.abc import Sequence
from dataclasses import asdict, dataclass
import math
from pathlib import Path
from tkinter import ttk
from types import SimpleNamespace
from typing import Callable, Protocol

from apps.common.uiTheme import (
    VEHICLE_GAUGE_REDLINE_THEME,
    VEHICLE_GAUGE_THEME,
    VehicleGaugeRedlineTheme,
)
from frontends.tk.automotive.vehicle_gauge_theme import (
    vehicle_gauge_theme_from_style_sheet,
)
from frontends.tk.automotive.vehicle_gauge_widgets import (
    DiagnosticsPanel,
    GearIndicator,
    LinearGauge,
    MetricTile,
    RoundGauge,
    TirePressurePanel,
)
from ui.theme import StyleSheet
from ui.automotive import (
    DiagnosticTroubleCode,
    DiagnosticsRequestHandlerIf,
    Gear,
    TirePosition,
    VehicleConnectionState,
    VehicleConnectionUiIf,
    VehicleDiagnosticsUiIf,
    VehicleTireUiIf,
    VehicleTripUiIf,
    VehicleUiIf,
)

class VehicleGaugeSnapshot(Protocol):
    """Minimum telemetry shape consumed directly by the gauge panel."""

    rpm: float | None
    speed_mph: float | None
    boost_psi: float | None
    throttle_pct: float | None
    coolant_temp_f: float | None
    intake_temp_f: float | None
    engine_load_pct: float | None
    control_voltage: float | None
    fuel_level_pct: float | None


@dataclass(frozen=True, slots=True)
class GaugeDefinition:
    """Maps one VehicleState field to a gauge presentation."""

    gauge_id: str
    title: str
    unit: str
    state_attribute: str
    minimum: float
    maximum: float
    major_step: float
    precision: int = 0
    shape: str = "round"
    value_scale: float = 1.0
    caution_low: float | None = None
    danger_low: float | None = None
    caution_high: float | None = None
    danger_high: float | None = None
    start_angle: float = 135.0
    sweep_angle: float = 270.0
    icon: str | None = None
    default_visible: bool = True
    intense_redline: bool = False
    redline_style: VehicleGaugeRedlineTheme = VEHICLE_GAUGE_REDLINE_THEME


class GaugeWidget(Protocol):
    """Operations shared by both instrument shapes."""

    def set_value(self, value: object) -> None: ...

    def set_connected(self, connected: bool) -> None: ...


@dataclass(slots=True)
class GaugeLayoutItem:
    """Persisted visibility and ordering for one gauge."""

    gauge_id: str
    visible: bool = True


DEFAULT_GAUGES: tuple[GaugeDefinition, ...] = (
    GaugeDefinition(
        "rpm", "RPM", "x1000", "rpm", 0, 8, 1,
        precision=1, value_scale=0.001, caution_high=6.0, danger_high=6.5,
        start_angle=140, sweep_angle=260, intense_redline=True,
    ),
    GaugeDefinition(
        "boost", "Boost", "psi", "boost_psi", -15, 25, 5,
        precision=1, caution_high=15, danger_high=18,
        start_angle=140, sweep_angle=260, intense_redline=True,
    ),
    GaugeDefinition(
        "speed", "mp/h", "", "speed_mph", 0, 160, 20,
        caution_high=120, danger_high=140,
        start_angle=140, sweep_angle=260, intense_redline=True,
    ),
    GaugeDefinition(
        "gear", "Gear", "", "gear", 0, 6, 1, shape="gear",
    ),
    GaugeDefinition(
        "throttle", "Throttle", "%", "throttle_pct", 0, 100, 20,
        start_angle=140, sweep_angle=260,
    ),
    GaugeDefinition(
        "coolant", "Coolant", "°F", "coolant_temp_f", 100, 260, 20,
        shape="linear", caution_high=220, danger_high=240, icon="coolant",
    ),
    GaugeDefinition(
        "intake", "Intake Air", "°F", "intake_temp_f", 0, 180, 20,
        shape="linear", caution_high=130, danger_high=155,
    ),
    GaugeDefinition(
        "load", "Engine Load", "%", "engine_load_pct", 0, 100, 20,
        shape="linear", caution_high=80, danger_high=95,
    ),
    GaugeDefinition(
        "voltage", "Voltage", "V", "control_voltage", 8, 16, 1,
        precision=1, shape="linear",
        caution_low=12.0, danger_low=10.5, caution_high=14.8, danger_high=15.5,
        icon="voltage",
    ),
    GaugeDefinition(
        "fuel", "Fuel Level", "%", "fuel_level_pct", 0, 100, 20,
        shape="linear", caution_low=20, danger_low=8, icon="fuel",
    ),
    GaugeDefinition(
        "odometer", "Odometer", "mi", "odometer_miles", 0, 1_000_000, 10_000,
        shape="metric",
    ),
    GaugeDefinition(
        "trip", "Trip", "mi", "trip_miles", 0, 10_000, 100,
        precision=1, shape="metric",
    ),
    GaugeDefinition(
        "economy", "Fuel Economy", "mpg", "fuel_economy_mpg", 0, 100, 10,
        precision=1, shape="metric",
    ),
    GaugeDefinition(
        "range", "Estimated Range", "mi", "estimated_range_miles", 0, 1_000, 100,
        shape="metric",
    ),
    GaugeDefinition(
        "ambient", "Outside Air", "°F", "ambient_temp_f", -40, 140, 20,
        shape="metric",
    ),
    GaugeDefinition(
        "tires", "Tire Pressure", "psi", "tire_pressures_psi", 0, 60, 5,
        shape="tires",
    ),
    GaugeDefinition(
        "diagnostics", "Engine Diagnostics", "", "diagnostic_trouble_codes",
        0, 1, 1, shape="diagnostics",
    ),
)


class VehicleGaugePanel(
    ttk.Frame,
    VehicleUiIf,
    VehicleConnectionUiIf,
    VehicleTripUiIf,
    VehicleTireUiIf,
    VehicleDiagnosticsUiIf,
):
    """Display vehicle state through explicit automotive UI contracts."""

    METERS_PER_MILE = 1609.344
    PASCALS_PER_PSI = 6894.757293168
    CUBIC_METERS_PER_US_GALLON = 0.003785411784

    def __init__(
        self,
        master: tk.Misc,
        *,
        definitions: tuple[GaugeDefinition, ...] = DEFAULT_GAUGES,
        config_path: str | Path | None = None,
        columns: int = 3,
        show_config_button: bool = True,
        panel_background: str | None = None,
    ) -> None:
        super().__init__(master)
        if columns < 1:
            raise ValueError("columns must be at least one")

        self._definitions = {item.gauge_id: item for item in definitions}
        self._config_path = Path(config_path).expanduser() if config_path else None
        self._preferred_columns = columns
        self._layout = self._load_layout(definitions)
        self._gauges: dict[str, GaugeWidget] = {}
        self._last_state: VehicleGaugeSnapshot | None = None
        self._connected = False
        self._connection_state = VehicleConnectionState.DISCONNECTED
        self._diagnostics_request_handler: DiagnosticsRequestHandlerIf | None = None
        self._contract_state = SimpleNamespace(
            tire_pressures_psi={},
            diagnostic_trouble_codes=(),
            mil_on=None,
        )
        self._style = VEHICLE_GAUGE_THEME
        self._panel_background = (
            panel_background
            if panel_background is not None
            else self._style.panel_background
        )

        self.configure(style="VehicleGauge.TFrame")
        self._configure_styles()

        self._toolbar = ttk.Frame(self, style="VehicleGauge.TFrame")
        self._toolbar.grid(row=0, column=0, sticky="ew", padx=8, pady=(6, 2))
        self._toolbar.columnconfigure(0, weight=1)

        self._status = ttk.Label(
            self._toolbar,
            text="VEHICLE DISCONNECTED",
            style="VehicleGaugeStatus.TLabel",
        )
        self._status.grid(row=0, column=0, sticky="w")

        if show_config_button:
            ttk.Button(
                self._toolbar,
                text="Arrange gauges",
                command=self.open_layout_editor,
            ).grid(row=0, column=1, sticky="e")

        self._gauge_host = tk.Frame(self, background=self._panel_background)
        self._gauge_host.grid(row=1, column=0, sticky="nsew", padx=8, pady=8)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.bind("<Configure>", self._on_panel_resize)

        self._rebuild_gauges()

    def set_style_sheet(self, sheet: StyleSheet) -> None:
        """Apply automotive gauge styling and rebuild rendered instruments."""

        self._style = vehicle_gauge_theme_from_style_sheet(sheet)
        self._configure_styles()
        self._gauge_host.configure(background=self._panel_background)
        self._rebuild_gauges()

    def update_state(
        self,
        state: VehicleGaugeSnapshot | None,
        *,
        connected: bool = True,
    ) -> None:
        """Update all gauges from a vehicle telemetry snapshot."""
        self._last_state = state
        self._connected = connected
        self._status.configure(
            text="VEHICLE CONNECTED" if connected else "VEHICLE DISCONNECTED",
            style=(
                "VehicleGaugeConnected.TLabel"
                if connected
                else "VehicleGaugeStatus.TLabel"
            ),
        )
        for gauge_id, gauge in self._gauges.items():
            definition = self._definitions[gauge_id]
            if definition.shape == "diagnostics":
                codes = None if state is None else getattr(
                    state, "diagnostic_trouble_codes", None
                )
                mil_on = None if state is None else getattr(state, "mil_on", None)
                gauge.set_connected(connected)
                if isinstance(gauge, DiagnosticsPanel):
                    gauge.set_diagnostics(codes, mil_on)
                continue
            value = None if state is None else getattr(state, definition.state_attribute, None)
            if value is not None and definition.shape not in {
                "gear", "diagnostics", "tires"
            }:
                value = float(value) * definition.value_scale
            gauge.set_connected(connected)
            gauge.set_value(value)

    def set_connection_state(
        self,
        state: VehicleConnectionState | None,
    ) -> None:
        """Set the displayed vehicle telemetry connection state."""
        self._connection_state = state or VehicleConnectionState.DISCONNECTED
        connected = state is VehicleConnectionState.CONNECTED
        labels = {
            VehicleConnectionState.CONNECTING: "VEHICLE CONNECTING",
            VehicleConnectionState.CONNECTED: "VEHICLE CONNECTED",
            VehicleConnectionState.ERROR: "VEHICLE ERROR",
            VehicleConnectionState.DISCONNECTED: "VEHICLE DISCONNECTED",
        }
        self.update_state(self._last_state, connected=connected)
        self._status.configure(text=labels[self._connection_state])

    def set_gear(self, gear: Gear | None) -> None:
        """Set the displayed transmission gear."""
        values = {
            Gear.REVERSE: "R",
            Gear.NEUTRAL: "N",
            Gear.FIRST: "1",
            Gear.SECOND: "2",
            Gear.THIRD: "3",
            Gear.FOURTH: "4",
            Gear.FIFTH: "5",
            Gear.SIXTH: "6",
        }
        self._set_contract_value("gear", values.get(gear))

    def set_vehicle_speed(self, speed_mps: float | None) -> None:
        """Set speed after converting metres per second to miles per hour."""
        self._set_contract_value(
            "speed_mph",
            None if speed_mps is None else speed_mps * 2.2369362920544,
        )

    def set_engine_speed(self, engine_speed_rad_s: float | None) -> None:
        """Set engine speed after converting radians per second to RPM."""
        self._set_contract_value(
            "rpm",
            None
            if engine_speed_rad_s is None
            else engine_speed_rad_s * 60.0 / (2.0 * math.pi),
        )

    def set_fuel_level(self, fuel_level_ratio: float | None) -> None:
        """Set fuel level after converting its ratio to percent."""
        self._set_contract_value(
            "fuel_level_pct",
            None if fuel_level_ratio is None else fuel_level_ratio * 100.0,
        )

    def set_throttle_position(
        self,
        throttle_position_ratio: float | None,
    ) -> None:
        """Set throttle position after converting its ratio to percent."""
        self._set_contract_value(
            "throttle_pct",
            None
            if throttle_position_ratio is None
            else throttle_position_ratio * 100.0,
        )

    def set_accelerator_position(
        self,
        accelerator_position_ratio: float | None,
    ) -> None:
        """Store accelerator position for compatible custom definitions."""
        self._set_contract_value(
            "accelerator_pedal_pct",
            None
            if accelerator_position_ratio is None
            else accelerator_position_ratio * 100.0,
        )

    def set_engine_load(self, engine_load_ratio: float | None) -> None:
        """Set engine load after converting its ratio to percent."""
        self._set_contract_value(
            "engine_load_pct",
            None if engine_load_ratio is None else engine_load_ratio * 100.0,
        )

    def set_coolant_temperature(
        self,
        coolant_temperature_k: float | None,
    ) -> None:
        """Set coolant temperature after converting kelvin to Fahrenheit."""
        self._set_contract_value(
            "coolant_temp_f",
            self._kelvin_to_fahrenheit(coolant_temperature_k),
        )

    def set_intake_air_temperature(
        self,
        intake_air_temperature_k: float | None,
    ) -> None:
        """Set intake temperature after converting kelvin to Fahrenheit."""
        self._set_contract_value(
            "intake_temp_f",
            self._kelvin_to_fahrenheit(intake_air_temperature_k),
        )

    def set_manifold_pressure(
        self,
        manifold_pressure_pa: float | None,
    ) -> None:
        """Store manifold pressure in kilopascals."""
        self._set_contract_value(
            "map_kpa",
            None if manifold_pressure_pa is None else manifold_pressure_pa / 1000.0,
        )

    def set_barometric_pressure(
        self,
        barometric_pressure_pa: float | None,
    ) -> None:
        """Store barometric pressure in kilopascals."""
        self._set_contract_value(
            "baro_kpa",
            None if barometric_pressure_pa is None else barometric_pressure_pa / 1000.0,
        )

    def set_boost_pressure(self, boost_pressure_pa: float | None) -> None:
        """Set boost pressure after converting pascals to PSI."""
        self._set_contract_value(
            "boost_psi",
            None
            if boost_pressure_pa is None
            else boost_pressure_pa / self.PASCALS_PER_PSI,
        )

    def set_mass_air_flow(self, mass_air_flow_kg_s: float | None) -> None:
        """Store mass airflow in grams per second."""
        self._set_contract_value(
            "maf_gps",
            None if mass_air_flow_kg_s is None else mass_air_flow_kg_s * 1000.0,
        )

    def set_control_voltage(self, control_voltage_v: float | None) -> None:
        """Set control-module voltage."""
        self._set_contract_value("control_voltage", control_voltage_v)

    def set_ambient_temperature(
        self,
        ambient_temperature_k: float | None,
    ) -> None:
        """Set ambient temperature after converting kelvin to Fahrenheit."""
        self._set_contract_value(
            "ambient_temp_f",
            self._kelvin_to_fahrenheit(ambient_temperature_k),
        )

    def set_engine_oil_temperature(
        self,
        engine_oil_temperature_k: float | None,
    ) -> None:
        """Store engine-oil temperature for compatible custom definitions."""
        self._set_contract_value(
            "engine_oil_temp_f",
            self._kelvin_to_fahrenheit(engine_oil_temperature_k),
        )

    def set_engine_oil_pressure(
        self,
        engine_oil_pressure_pa: float | None,
    ) -> None:
        """Store engine-oil pressure for compatible custom definitions."""
        self._set_contract_value(
            "engine_oil_pressure_psi",
            None
            if engine_oil_pressure_pa is None
            else engine_oil_pressure_pa / self.PASCALS_PER_PSI,
        )

    def set_transmission_temperature(
        self,
        transmission_temperature_k: float | None,
    ) -> None:
        """Store transmission temperature for custom gauge definitions."""
        self._set_contract_value(
            "transmission_temp_f",
            self._kelvin_to_fahrenheit(transmission_temperature_k),
        )

    def set_odometer(self, distance_m: float | None) -> None:
        """Set odometer distance after converting metres to miles."""
        self._set_contract_value("odometer_miles", self._meters_to_miles(distance_m))

    def set_trip_distance(self, distance_m: float | None) -> None:
        """Set trip distance after converting metres to miles."""
        self._set_contract_value("trip_miles", self._meters_to_miles(distance_m))

    def set_estimated_range(self, distance_m: float | None) -> None:
        """Set estimated range after converting metres to miles."""
        self._set_contract_value(
            "estimated_range_miles",
            self._meters_to_miles(distance_m),
        )

    def set_instantaneous_fuel_consumption(
        self,
        fuel_consumption_m3_per_m: float | None,
    ) -> None:
        """Set instantaneous fuel economy after converting to MPG."""
        self._set_contract_value(
            "instantaneous_fuel_economy_mpg",
            self._fuel_consumption_to_mpg(fuel_consumption_m3_per_m),
        )

    def set_average_fuel_consumption(
        self,
        fuel_consumption_m3_per_m: float | None,
    ) -> None:
        """Set average fuel economy after converting to MPG."""
        self._set_contract_value(
            "fuel_economy_mpg",
            self._fuel_consumption_to_mpg(fuel_consumption_m3_per_m),
        )

    def set_fuel_used(self, fuel_volume_m3: float | None) -> None:
        """Store trip fuel volume after converting cubic metres to gallons."""
        self._set_contract_value(
            "fuel_used_gallons",
            None
            if fuel_volume_m3 is None
            else fuel_volume_m3 / self.CUBIC_METERS_PER_US_GALLON,
        )

    def set_tire_pressure(
        self,
        position: TirePosition,
        pressure_pa: float | None,
    ) -> None:
        """Set one tire pressure after converting pascals to PSI."""
        pressures = dict(self._contract_state.tire_pressures_psi)
        key = self._tire_key(position)
        if pressure_pa is None:
            pressures.pop(key, None)
        else:
            pressures[key] = pressure_pa / self.PASCALS_PER_PSI
        self._set_contract_value("tire_pressures_psi", pressures)

    def set_tire_temperature(
        self,
        position: TirePosition,
        temperature_k: float | None,
    ) -> None:
        """Store one tire temperature for compatible custom definitions."""
        temperatures = dict(
            getattr(self._contract_state, "tire_temperatures_f", {})
        )
        temperatures[self._tire_key(position)] = self._kelvin_to_fahrenheit(
            temperature_k
        )
        self._set_contract_value("tire_temperatures_f", temperatures)

    def set_tire_pressure_warning(
        self,
        position: TirePosition,
        active: bool | None,
    ) -> None:
        """Store one tire pressure-warning state."""
        warnings = dict(getattr(self._contract_state, "tire_warnings", {}))
        warnings[self._tire_key(position)] = active
        self._set_contract_value("tire_warnings", warnings)

    def set_malfunction_indicator(self, active: bool | None) -> None:
        """Set the malfunction indicator state."""
        self._set_contract_value("mil_on", active)

    def set_trouble_codes(
        self,
        trouble_codes: Sequence[DiagnosticTroubleCode],
    ) -> None:
        """Replace the displayed diagnostic trouble codes."""
        self._set_contract_value(
            "diagnostic_trouble_codes",
            tuple(item.code for item in trouble_codes),
        )

    def set_emissions_readiness(self, ready: bool | None) -> None:
        """Store emissions-readiness state for diagnostics presentation."""
        self._set_contract_value("emissions_ready", ready)

    def set_diagnostics_request_handler(
        self,
        handler: DiagnosticsRequestHandlerIf | None,
    ) -> None:
        """Set the handler for future diagnostic actions."""
        self._diagnostics_request_handler = handler

    def _set_contract_value(self, name: str, value: object) -> None:
        setattr(self._contract_state, name, value)
        self.update_state(
            self._contract_state,
            connected=(
                self._connection_state is VehicleConnectionState.CONNECTED
            ),
        )

    @staticmethod
    def _kelvin_to_fahrenheit(value: float | None) -> float | None:
        return None if value is None else (value - 273.15) * 9.0 / 5.0 + 32.0

    def _meters_to_miles(self, value: float | None) -> float | None:
        return None if value is None else value / self.METERS_PER_MILE

    def _fuel_consumption_to_mpg(self, value: float | None) -> float | None:
        if value is None or value <= 0.0:
            return None
        return (
            self.CUBIC_METERS_PER_US_GALLON
            / value
            / self.METERS_PER_MILE
        )

    @staticmethod
    def _tire_key(position: TirePosition) -> str:
        return {
            TirePosition.FRONT_LEFT: "front_left",
            TirePosition.FRONT_RIGHT: "front_right",
            TirePosition.REAR_LEFT: "rear_left",
            TirePosition.REAR_RIGHT: "rear_right",
        }[position]

    def set_gauge_visible(self, gauge_id: str, visible: bool) -> None:
        """Show or hide a gauge by its stable identifier."""
        item = self._layout_item(gauge_id)
        item.visible = visible
        self._persist_and_rebuild()

    def move_gauge(self, gauge_id: str, offset: int) -> None:
        """Move a gauge earlier or later in the configured order."""
        index = next(
            (position for position, item in enumerate(self._layout) if item.gauge_id == gauge_id),
            None,
        )
        if index is None:
            raise KeyError(gauge_id)
        destination = max(0, min(len(self._layout) - 1, index + offset))
        if destination == index:
            return
        item = self._layout.pop(index)
        self._layout.insert(destination, item)
        self._persist_and_rebuild()

    def open_layout_editor(self) -> None:
        """Open a modal-ish editor for visibility and gauge order."""
        editor = tk.Toplevel(self)
        editor.title("Arrange Vehicle Gauges")
        editor.configure(background=self._style.panel_background)
        editor.transient(self.winfo_toplevel())
        editor.geometry("470x520")

        ttk.Label(
            editor,
            text="Gauge layout",
            style="VehicleGaugeHeading.TLabel",
        ).pack(anchor="w", padx=16, pady=(14, 4))
        ttk.Label(
            editor,
            text="Enable gauges and move them into the order used by the panel.",
            style="VehicleGauge.TLabel",
        ).pack(anchor="w", padx=16, pady=(0, 10))

        list_host = ttk.Frame(editor, style="VehicleGauge.TFrame")
        list_host.pack(fill="both", expand=True, padx=16, pady=4)

        variables: dict[str, tk.BooleanVar] = {}
        selected_id = tk.StringVar(value=self._layout[0].gauge_id if self._layout else "")

        def render_rows() -> None:
            for child in list_host.winfo_children():
                child.destroy()
            for row_index, item in enumerate(self._layout):
                definition = self._definitions[item.gauge_id]
                variables.setdefault(item.gauge_id, tk.BooleanVar(value=item.visible))
                row = ttk.Frame(list_host, style="VehicleGauge.TFrame")
                row.grid(row=row_index, column=0, sticky="ew", pady=2)
                row.columnconfigure(1, weight=1)
                ttk.Radiobutton(
                    row,
                    variable=selected_id,
                    value=item.gauge_id,
                ).grid(row=0, column=0, padx=(0, 6))
                ttk.Checkbutton(
                    row,
                    text=f"{definition.title} ({definition.unit})",
                    variable=variables[item.gauge_id],
                ).grid(row=0, column=1, sticky="w")
                ttk.Label(
                    row,
                    text=str(row_index + 1),
                    style="VehicleGauge.TLabel",
                ).grid(row=0, column=2, padx=8)
            list_host.columnconfigure(0, weight=1)

        def move_selected(offset: int) -> None:
            gauge_id = selected_id.get()
            index = next(
                (i for i, item in enumerate(self._layout) if item.gauge_id == gauge_id),
                None,
            )
            if index is None:
                return
            destination = max(0, min(len(self._layout) - 1, index + offset))
            if destination != index:
                item = self._layout.pop(index)
                self._layout.insert(destination, item)
                render_rows()

        def apply() -> None:
            for item in self._layout:
                item.visible = variables[item.gauge_id].get()
            self._save_layout()
            self._rebuild_gauges()
            editor.destroy()

        render_rows()

        controls = ttk.Frame(editor, style="VehicleGauge.TFrame")
        controls.pack(fill="x", padx=16, pady=8)
        ttk.Button(controls, text="Move up", command=lambda: move_selected(-1)).pack(side="left")
        ttk.Button(controls, text="Move down", command=lambda: move_selected(1)).pack(side="left", padx=8)
        ttk.Button(controls, text="Cancel", command=editor.destroy).pack(side="right")
        ttk.Button(controls, text="Apply", command=apply).pack(side="right", padx=8)

        editor.grab_set()

    def _configure_styles(self) -> None:
        style = ttk.Style(self)
        style.configure(
            "VehicleGauge.TFrame",
            background=self._panel_background,
        )
        style.configure(
            "VehicleGauge.TLabel",
            background=self._style.panel_background,
            foreground=self._style.panel_foreground,
        )
        style.configure(
            "VehicleGaugeHeading.TLabel",
            background=self._style.panel_background,
            foreground=self._style.panel_foreground,
            font=(self._style.font_family, 16, "bold"),
        )
        style.configure(
            "VehicleGaugeStatus.TLabel",
            background=self._style.panel_background,
            foreground=self._style.panel_status_disconnected,
            font=(self._style.font_family, 11, "bold"),
        )
        style.configure(
            "VehicleGaugeConnected.TLabel",
            background=self._style.panel_background,
            foreground=self._style.panel_status_connected,
            font=(self._style.font_family, 11, "bold"),
        )

    def _load_layout(
        self,
        definitions: tuple[GaugeDefinition, ...],
    ) -> list[GaugeLayoutItem]:
        default = [
            GaugeLayoutItem(item.gauge_id, item.default_visible)
            for item in definitions
        ]
        if self._config_path is None or not self._config_path.exists():
            return default
        try:
            payload = json.loads(self._config_path.read_text(encoding="utf-8"))
            loaded = [GaugeLayoutItem(**item) for item in payload.get("gauges", [])]
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return default

        known_ids = {item.gauge_id for item in definitions}
        result = [item for item in loaded if item.gauge_id in known_ids]
        existing = {item.gauge_id for item in result}
        result.extend(item for item in default if item.gauge_id not in existing)
        return result

    def _save_layout(self) -> None:
        if self._config_path is None:
            return
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"gauges": [asdict(item) for item in self._layout]}
        self._config_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def _persist_and_rebuild(self) -> None:
        self._save_layout()
        self._rebuild_gauges()

    def _layout_item(self, gauge_id: str) -> GaugeLayoutItem:
        for item in self._layout:
            if item.gauge_id == gauge_id:
                return item
        raise KeyError(gauge_id)

    def _rebuild_gauges(self) -> None:
        for child in self._gauge_host.winfo_children():
            child.destroy()
        self._gauges.clear()

        visible = [item for item in self._layout if item.visible]
        columns = self._effective_columns()
        for column in range(columns):
            self._gauge_host.columnconfigure(column, weight=1, uniform="gauge")

        row = 0
        column = 0
        for item in visible:
            definition = self._definitions[item.gauge_id]
            column_span = (
                2
                if definition.shape in {"linear", "diagnostics", "tires"}
                and columns > 1
                else 1
            )
            if column + column_span > columns:
                row += 1
                column = 0
            common_options = {
                "title": definition.title,
                "unit": definition.unit,
                "minimum": definition.minimum,
                "maximum": definition.maximum,
                "precision": definition.precision,
                "style": self._style,
            }
            if definition.shape == "linear":
                gauge = LinearGauge(
                    self._gauge_host,
                    caution_low=definition.caution_low,
                    danger_low=definition.danger_low,
                    caution_high=definition.caution_high,
                    danger_high=definition.danger_high,
                    icon=definition.icon,
                    **common_options,
                )
            elif definition.shape == "gear":
                gauge = GearIndicator(self._gauge_host, style=self._style)
            elif definition.shape == "metric":
                gauge = MetricTile(
                    self._gauge_host,
                    title=definition.title,
                    unit=definition.unit,
                    precision=definition.precision,
                    style=self._style,
                )
            elif definition.shape == "tires":
                gauge = TirePressurePanel(self._gauge_host, style=self._style)
            elif definition.shape == "diagnostics":
                gauge = DiagnosticsPanel(self._gauge_host, style=self._style)
            else:
                gauge = RoundGauge(
                    self._gauge_host,
                    major_step=definition.major_step,
                    caution_start=definition.caution_high,
                    danger_start=definition.danger_high,
                    intense_redline=definition.intense_redline,
                    redline_style=definition.redline_style,
                    start_angle=definition.start_angle,
                    sweep_angle=definition.sweep_angle,
                    size=220,
                    **common_options,
                )
            gauge.grid(
                row=row,
                column=column,
                columnspan=column_span,
                sticky="nsew" if definition.shape in {"round", "gear"} else "ew",
                padx=5,
                pady=5,
            )
            if definition.shape in {"round", "gear"}:
                self._gauge_host.rowconfigure(row, weight=1, minsize=190)
            elif definition.shape == "tires":
                self._gauge_host.rowconfigure(row, weight=0, minsize=170)
            else:
                self._gauge_host.rowconfigure(row, weight=0, minsize=112)
            self._gauges[item.gauge_id] = gauge
            column += column_span
            if column >= columns:
                row += 1
                column = 0

        if not visible:
            ttk.Label(
                self._gauge_host,
                text="No gauges are enabled. Use Arrange gauges to add one.",
                style="VehicleGauge.TLabel",
            ).grid(row=0, column=0, padx=20, pady=40)

        self.update_state(self._last_state, connected=self._connected)

    def _effective_columns(self) -> int:
        width = self.winfo_width()
        if width <= 1:
            return self._preferred_columns
        return max(1, min(self._preferred_columns, width // 210))

    def _on_panel_resize(self, _event: tk.Event[tk.Misc]) -> None:
        # Delay so repeated Configure events collapse into one layout pass.
        callback: Callable[[], None] = self._rebuild_if_column_count_changed
        pending = getattr(self, "_resize_after_id", None)
        if pending is not None:
            self.after_cancel(pending)
        self._resize_after_id = self.after(120, callback)

    def _rebuild_if_column_count_changed(self) -> None:
        self._resize_after_id = None
        current_columns = 0
        if self._gauges:
            current_columns = max(
                int(gauge.grid_info().get("column", 0))
                + int(gauge.grid_info().get("columnspan", 1))
                for gauge in self._gauges.values()
            )
        if current_columns != self._effective_columns():
            self._rebuild_gauges()
