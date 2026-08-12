# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Curses implementation of all automotive UI contracts."""

from __future__ import annotations

import curses
from collections.abc import Sequence
from threading import Lock

from ui.automotive import (
    DiagnosticTroubleCode,
    DiagnosticsRequestHandlerIf,
    ExteriorLight,
    Gear,
    SeatPosition,
    TirePosition,
    VehicleBodyUiIf,
    VehicleConnectionState,
    VehicleConnectionUiIf,
    VehicleDiagnosticsUiIf,
    VehicleOpening,
    VehicleTireUiIf,
    VehicleTripUiIf,
    VehicleUiIf,
)
from ui.ui_if import UiIf


class AutomotiveDemoUi(
    UiIf,
    VehicleUiIf,
    VehicleTripUiIf,
    VehicleTireUiIf,
    VehicleBodyUiIf,
    VehicleDiagnosticsUiIf,
    VehicleConnectionUiIf,
):
    """Render automotive contract updates in a simple terminal dashboard."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._running = False
        self._imperial = False
        self._values: dict[str, object] = {}
        self._tire_values: dict[tuple[str, TirePosition], object] = {}
        self._body_values: dict[tuple[str, object], object] = {}
        self._trouble_codes: tuple[DiagnosticTroubleCode, ...] = ()
        self._diagnostics_handler: DiagnosticsRequestHandlerIf | None = None

    def initialize(self) -> bool:
        self._running = True
        return True

    def shutdown(self) -> None:
        self._running = False

    def _set(self, name: str, value: object) -> None:
        with self._lock:
            self._values[name] = value

    def set_gear(self, gear: Gear | None) -> None:
        self._set("gear", gear)

    def set_vehicle_speed(self, speed_mps: float | None) -> None:
        self._set("speed_mps", speed_mps)

    def set_engine_speed(self, engine_speed_rad_s: float | None) -> None:
        self._set("engine_speed_rad_s", engine_speed_rad_s)

    def set_fuel_level(self, fuel_level_ratio: float | None) -> None:
        self._set("fuel_level_ratio", fuel_level_ratio)

    def set_throttle_position(self, throttle_position_ratio: float | None) -> None:
        self._set("throttle_position_ratio", throttle_position_ratio)

    def set_accelerator_position(
        self,
        accelerator_position_ratio: float | None,
    ) -> None:
        self._set("accelerator_position_ratio", accelerator_position_ratio)

    def set_engine_load(self, engine_load_ratio: float | None) -> None:
        self._set("engine_load_ratio", engine_load_ratio)

    def set_coolant_temperature(
        self,
        coolant_temperature_k: float | None,
    ) -> None:
        self._set("coolant_temperature_k", coolant_temperature_k)

    def set_intake_air_temperature(
        self,
        intake_air_temperature_k: float | None,
    ) -> None:
        self._set("intake_air_temperature_k", intake_air_temperature_k)

    def set_manifold_pressure(self, manifold_pressure_pa: float | None) -> None:
        self._set("manifold_pressure_pa", manifold_pressure_pa)

    def set_barometric_pressure(self, barometric_pressure_pa: float | None) -> None:
        self._set("barometric_pressure_pa", barometric_pressure_pa)

    def set_boost_pressure(self, boost_pressure_pa: float | None) -> None:
        self._set("boost_pressure_pa", boost_pressure_pa)

    def set_mass_air_flow(self, mass_air_flow_kg_s: float | None) -> None:
        self._set("mass_air_flow_kg_s", mass_air_flow_kg_s)

    def set_control_voltage(self, control_voltage_v: float | None) -> None:
        self._set("control_voltage_v", control_voltage_v)

    def set_ambient_temperature(self, ambient_temperature_k: float | None) -> None:
        self._set("ambient_temperature_k", ambient_temperature_k)

    def set_engine_oil_temperature(
        self,
        engine_oil_temperature_k: float | None,
    ) -> None:
        self._set("engine_oil_temperature_k", engine_oil_temperature_k)

    def set_engine_oil_pressure(
        self,
        engine_oil_pressure_pa: float | None,
    ) -> None:
        self._set("engine_oil_pressure_pa", engine_oil_pressure_pa)

    def set_transmission_temperature(
        self,
        transmission_temperature_k: float | None,
    ) -> None:
        self._set("transmission_temperature_k", transmission_temperature_k)

    def set_odometer(self, distance_m: float | None) -> None:
        self._set("odometer_m", distance_m)

    def set_trip_distance(self, distance_m: float | None) -> None:
        self._set("trip_distance_m", distance_m)

    def set_estimated_range(self, distance_m: float | None) -> None:
        self._set("estimated_range_m", distance_m)

    def set_instantaneous_fuel_consumption(
        self,
        fuel_consumption_m3_per_m: float | None,
    ) -> None:
        self._set("instantaneous_fuel_consumption_m3_per_m", fuel_consumption_m3_per_m)

    def set_average_fuel_consumption(
        self,
        fuel_consumption_m3_per_m: float | None,
    ) -> None:
        self._set("average_fuel_consumption_m3_per_m", fuel_consumption_m3_per_m)

    def set_fuel_used(self, fuel_volume_m3: float | None) -> None:
        self._set("fuel_used_m3", fuel_volume_m3)

    def set_tire_pressure(
        self,
        position: TirePosition,
        pressure_pa: float | None,
    ) -> None:
        with self._lock:
            self._tire_values[("pressure", position)] = pressure_pa

    def set_tire_temperature(
        self,
        position: TirePosition,
        temperature_k: float | None,
    ) -> None:
        with self._lock:
            self._tire_values[("temperature", position)] = temperature_k

    def set_tire_pressure_warning(
        self,
        position: TirePosition,
        active: bool | None,
    ) -> None:
        with self._lock:
            self._tire_values[("warning", position)] = active

    def set_opening_state(
        self,
        opening: VehicleOpening,
        is_open: bool | None,
    ) -> None:
        with self._lock:
            self._body_values[("opening", opening)] = is_open

    def set_seat_belt_state(
        self,
        seat: SeatPosition,
        fastened: bool | None,
    ) -> None:
        with self._lock:
            self._body_values[("belt", seat)] = fastened

    def set_exterior_light_state(
        self,
        light: ExteriorLight,
        active: bool | None,
    ) -> None:
        with self._lock:
            self._body_values[("light", light)] = active

    def set_parking_brake(self, applied: bool | None) -> None:
        self._set("parking_brake", applied)

    def set_connection_state(
        self,
        state: VehicleConnectionState | None,
    ) -> None:
        self._set("connection", state)

    def set_malfunction_indicator(self, active: bool | None) -> None:
        self._set("malfunction_indicator", active)

    def set_trouble_codes(
        self,
        trouble_codes: Sequence[DiagnosticTroubleCode],
    ) -> None:
        with self._lock:
            self._trouble_codes = tuple(trouble_codes)

    def set_emissions_readiness(self, ready: bool | None) -> None:
        self._set("emissions_ready", ready)

    def set_diagnostics_request_handler(
        self,
        handler: DiagnosticsRequestHandlerIf | None,
    ) -> None:
        with self._lock:
            self._diagnostics_handler = handler

    def run(self) -> None:
        """Run the terminal UI until the user requests shutdown."""
        curses.wrapper(self._run)

    def _run(self, screen: curses.window) -> None:
        screen.nodelay(True)
        screen.keypad(True)
        try:
            curses.curs_set(0)
        except curses.error:
            pass
        if curses.has_colors():
            curses.start_color()
            curses.use_default_colors()
            curses.init_pair(1, curses.COLOR_CYAN, -1)
            curses.init_pair(2, curses.COLOR_GREEN, -1)
            curses.init_pair(3, curses.COLOR_YELLOW, -1)
            curses.init_pair(4, curses.COLOR_RED, -1)

        while self._running:
            key = screen.getch()
            if key in (ord("q"), 27):
                self._running = False
            elif key == ord("u"):
                self._imperial = not self._imperial
            elif key == ord("c"):
                with self._lock:
                    handler = self._diagnostics_handler
                if handler is not None:
                    handler.request_clear_diagnostics()
            self._draw(screen)
            curses.napms(100)

    def _draw(self, screen: curses.window) -> None:
        with self._lock:
            values = dict(self._values)
            tires = dict(self._tire_values)
            body = dict(self._body_values)
            codes = self._trouble_codes
        screen.erase()
        self._text(screen, 0, 0, "OpenRoadCode Automotive UI Demo", curses.A_BOLD)
        self._text(screen, 1, 0, "q: quit   u: units   c: clear diagnostics")
        connection = values.get("connection")
        connection_text = connection.name if isinstance(connection, VehicleConnectionState) else "--"
        self._text(screen, 0, 45, connection_text, self._color(2))

        gear = values.get("gear")
        gear_text = gear.name if isinstance(gear, Gear) else "--"
        self._section(screen, 3, 0, "DRIVING")
        self._field(screen, 4, 0, "Gear", gear_text)
        self._field(screen, 5, 0, "Speed", self._speed(values.get("speed_mps")))
        self._field(screen, 6, 0, "Engine", self._angular_speed(values.get("engine_speed_rad_s")))
        self._field(screen, 7, 0, "Throttle", self._ratio(values.get("throttle_position_ratio")))
        self._field(screen, 8, 0, "Fuel", self._ratio(values.get("fuel_level_ratio")))

        self._section(screen, 3, 28, "TEMPERATURE / PRESSURE")
        self._field(screen, 4, 28, "Coolant", self._temperature(values.get("coolant_temperature_k")))
        self._field(screen, 5, 28, "Oil", self._temperature(values.get("engine_oil_temperature_k")))
        self._field(screen, 6, 28, "Oil pressure", self._pressure(values.get("engine_oil_pressure_pa")))
        self._field(screen, 7, 28, "Boost", self._pressure(values.get("boost_pressure_pa"), signed=True))
        self._field(screen, 8, 28, "Ambient", self._temperature(values.get("ambient_temperature_k")))

        self._section(screen, 10, 0, "TRIP")
        self._field(screen, 11, 0, "Odometer", self._distance(values.get("odometer_m")))
        self._field(screen, 12, 0, "Trip", self._distance(values.get("trip_distance_m")))
        self._field(screen, 13, 0, "Range", self._distance(values.get("estimated_range_m")))
        self._field(screen, 14, 0, "Average", self._consumption(values.get("average_fuel_consumption_m3_per_m")))

        self._section(screen, 10, 38, "TIRES")
        for offset, position in enumerate(TirePosition):
            pressure = self._pressure(tires.get(("pressure", position)))
            warning = tires.get(("warning", position))
            marker = " !" if warning else ""
            self._field(screen, 11 + offset, 38, position.name, pressure + marker)

        self._section(screen, 16, 0, "BODY / DIAGNOSTICS")
        door = body.get(("opening", VehicleOpening.FRONT_LEFT_DOOR))
        belt = body.get(("belt", SeatPosition.DRIVER))
        self._field(screen, 17, 0, "Driver door", self._state(door, "OPEN", "closed"))
        self._field(screen, 18, 0, "Driver belt", self._state(belt, "fastened", "UNFASTENED"))
        self._field(screen, 17, 30, "Parking brake", self._state(values.get("parking_brake"), "APPLIED", "released"))
        self._field(screen, 18, 30, "MIL", self._state(values.get("malfunction_indicator"), "ON", "off"))
        code_text = ", ".join(code.code for code in codes) if codes else "none"
        self._field(screen, 19, 0, "Trouble codes", code_text)
        screen.refresh()

    @staticmethod
    def _text(screen: curses.window, row: int, column: int, value: str, attr: int = 0) -> None:
        try:
            height, width = screen.getmaxyx()
            if row < height and column < width:
                screen.addnstr(row, column, value, max(0, width - column - 1), attr)
        except curses.error:
            pass

    def _section(self, screen: curses.window, row: int, column: int, title: str) -> None:
        self._text(screen, row, column, title, curses.A_BOLD | self._color(1))

    def _field(self, screen: curses.window, row: int, column: int, label: str, value: str) -> None:
        self._text(screen, row, column, f"{label:<16} {value}")

    @staticmethod
    def _number(value: object) -> float | None:
        return float(value) if isinstance(value, (int, float)) else None

    def _speed(self, value: object) -> str:
        number = self._number(value)
        if number is None:
            return "--"
        return f"{number * (2.236936 if self._imperial else 3.6):.1f} {'mph' if self._imperial else 'km/h'}"

    @staticmethod
    def _angular_speed(value: object) -> str:
        number = AutomotiveDemoUi._number(value)
        return "--" if number is None else f"{number * 9.549297:.0f} rpm"

    @staticmethod
    def _ratio(value: object) -> str:
        number = AutomotiveDemoUi._number(value)
        return "--" if number is None else f"{number * 100.0:.0f}%"

    def _temperature(self, value: object) -> str:
        number = self._number(value)
        if number is None:
            return "--"
        celsius = number - 273.15
        return f"{celsius * 1.8 + 32.0:.1f} °F" if self._imperial else f"{celsius:.1f} °C"

    def _pressure(self, value: object, signed: bool = False) -> str:
        number = self._number(value)
        if number is None:
            return "--"
        converted = number / (6894.757 if self._imperial else 1000.0)
        sign = "+" if signed and converted >= 0 else ""
        return f"{sign}{converted:.1f} {'psi' if self._imperial else 'kPa'}"

    def _distance(self, value: object) -> str:
        number = self._number(value)
        if number is None:
            return "--"
        return f"{number / (1609.344 if self._imperial else 1000.0):.1f} {'mi' if self._imperial else 'km'}"

    def _consumption(self, value: object) -> str:
        number = self._number(value)
        if number is None or number <= 0:
            return "--"
        if self._imperial:
            return f"{2.352145833e-6 / number:.1f} mpg"
        return f"{number * 100_000_000.0:.1f} L/100 km"

    @staticmethod
    def _state(value: object, true_text: str, false_text: str) -> str:
        if value is None:
            return "--"
        return true_text if value is True else false_text

    @staticmethod
    def _color(pair: int) -> int:
        return curses.color_pair(pair) if curses.has_colors() else 0
