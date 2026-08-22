# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Reusable curses presentation for SI-normalized vehicle telemetry."""

from __future__ import annotations

import curses
import math
from typing import Protocol

from frontends.tui.curses_helpers import addstr, format_value

RPM_PER_RAD_S = 60.0 / (2.0 * math.pi)
MPH_PER_MPS = 2.2369362920544
PSI_PER_PA = 0.00014503773773020923
KPA_PER_PA = 0.001
GPS_PER_KGPS = 1000.0


class VehicleSnapshot(Protocol):
    timestamp: object
    engine_speed_rad_s: float | None
    vehicle_speed_m_s: float | None
    boost_pressure_pa: float | None
    coolant_temperature_k: float | None
    intake_air_temperature_k: float | None
    throttle_position: float | None
    accelerator_pedal_position: float | None
    engine_load: float | None
    intake_manifold_pressure_pa: float | None
    barometric_pressure_pa: float | None
    mass_air_flow_kg_s: float | None
    fuel_level: float | None
    control_voltage_v: float | None


def _fahrenheit(kelvin: float | None) -> float | None:
    if kelvin is None:
        return None
    return (kelvin - 273.15) * 9.0 / 5.0 + 32.0


def _percent(fraction: float | None) -> float | None:
    return None if fraction is None else fraction * 100.0


def vehicle_fields(
    state: VehicleSnapshot | None,
) -> tuple[tuple[str, str], ...]:
    """Return presentation-unit labels and values for an SI snapshot."""
    labels = (
        "Engine RPM", "Vehicle speed", "Boost", "Coolant", "Intake air",
        "Throttle", "Accelerator", "Engine load", "MAP", "Barometric",
        "Mass airflow", "Fuel level", "Module voltage",
    )
    if state is None:
        return tuple((label, "--") for label in labels)

    rpm = (
        None
        if state.engine_speed_rad_s is None
        else state.engine_speed_rad_s * RPM_PER_RAD_S
    )
    speed_mph = (
        None
        if state.vehicle_speed_m_s is None
        else state.vehicle_speed_m_s * MPH_PER_MPS
    )
    boost_psi = (
        None
        if state.boost_pressure_pa is None
        else state.boost_pressure_pa * PSI_PER_PA
    )
    map_kpa = (
        None
        if state.intake_manifold_pressure_pa is None
        else state.intake_manifold_pressure_pa * KPA_PER_PA
    )
    baro_kpa = (
        None
        if state.barometric_pressure_pa is None
        else state.barometric_pressure_pa * KPA_PER_PA
    )
    maf_gps = (
        None
        if state.mass_air_flow_kg_s is None
        else state.mass_air_flow_kg_s * GPS_PER_KGPS
    )

    return (
        ("Engine RPM", format_value(rpm, "rpm", 0)),
        ("Vehicle speed", format_value(speed_mph, "mph")),
        ("Boost", format_value(boost_psi, "psi")),
        ("Coolant", format_value(_fahrenheit(state.coolant_temperature_k), "°F")),
        ("Intake air", format_value(_fahrenheit(state.intake_air_temperature_k), "°F")),
        ("Throttle", format_value(_percent(state.throttle_position), "%")),
        ("Accelerator", format_value(_percent(state.accelerator_pedal_position), "%")),
        ("Engine load", format_value(_percent(state.engine_load), "%")),
        ("MAP", format_value(map_kpa, "kPa")),
        ("Barometric", format_value(baro_kpa, "kPa")),
        ("Mass airflow", format_value(maf_gps, "g/s", 2)),
        ("Fuel level", format_value(_percent(state.fuel_level), "%")),
        ("Module voltage", format_value(state.control_voltage_v, "V", 2)),
    )


class VehicleDashboardView:
    """Render vehicle telemetry into a curses window."""

    def render(
        self,
        screen,
        state: VehicleSnapshot | None,
        status: str,
        connected: bool,
        controls: str | None = None,
    ) -> None:
        screen.erase()
        height, width = screen.getmaxyx()
        title_attr = curses.A_BOLD | (curses.color_pair(1) if curses.has_colors() else 0)
        addstr(screen, 0, 2, "OpenRoadCode Vehicle", title_attr)
        addstr(screen, 1, 0, "─" * max(0, width - 1))
        connection = "CONNECTED" if connected else "DISCONNECTED"
        connection_attr = curses.A_BOLD | (
            curses.color_pair(2 if connected else 3) if curses.has_colors() else 0
        )
        addstr(screen, 2, 2, connection, connection_attr)
        if state is not None:
            timestamp = getattr(state.timestamp, "strftime", lambda _fmt: "--:--:--")
            addstr(screen, 2, max(24, width - 24), f"Updated {timestamp('%H:%M:%S')}")
        fields = vehicle_fields(state)
        two_columns = width >= 72
        rows_per_column = (len(fields) + 1) // 2 if two_columns else len(fields)
        column_width = width // 2 if two_columns else width
        for index, (label, value) in enumerate(fields):
            column_index = index // rows_per_column if two_columns else 0
            row = 4 + index % rows_per_column
            column = 2 + column_index * column_width
            addstr(screen, row, column, f"{label:<16}", curses.A_DIM)
            addstr(screen, row, column + 17, value, curses.A_BOLD)
        footer_row = min(height - 2, 5 + rows_per_column)
        addstr(screen, footer_row, 0, "─" * max(0, width - 1))
        addstr(screen, footer_row + 1, 2, status)
        controls = controls or "q: quit"
        addstr(screen, height - 1, max(2, width - len(controls) - 2), controls)
        screen.refresh()
