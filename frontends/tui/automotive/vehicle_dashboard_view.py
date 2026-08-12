# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Reusable curses presentation for vehicle telemetry snapshots."""

from __future__ import annotations

import curses
from typing import Protocol

from frontends.tui.curses_helpers import addstr, format_value


class VehicleSnapshot(Protocol):
    timestamp: object
    rpm: float | None
    speed_mph: float | None
    boost_psi: float | None
    coolant_temp_f: float | None
    intake_temp_f: float | None
    throttle_pct: float | None
    accelerator_pedal_pct: float | None
    engine_load_pct: float | None
    map_kpa: int | None
    baro_kpa: int | None
    maf_gps: float | None
    fuel_level_pct: float | None
    control_voltage: float | None


def vehicle_fields(
    state: VehicleSnapshot | None,
) -> tuple[tuple[str, str], ...]:
    """Return formatted labels and values for a vehicle snapshot."""
    labels = (
        "Engine RPM", "Vehicle speed", "Boost", "Coolant", "Intake air",
        "Throttle", "Accelerator", "Engine load", "MAP", "Barometric",
        "Mass airflow", "Fuel level", "Module voltage",
    )
    if state is None:
        return tuple((label, "--") for label in labels)
    return (
        ("Engine RPM", format_value(state.rpm, "rpm", 0)),
        ("Vehicle speed", format_value(state.speed_mph, "mph")),
        ("Boost", format_value(state.boost_psi, "psi")),
        ("Coolant", format_value(state.coolant_temp_f, "°F")),
        ("Intake air", format_value(state.intake_temp_f, "°F")),
        ("Throttle", format_value(state.throttle_pct, "%")),
        ("Accelerator", format_value(state.accelerator_pedal_pct, "%")),
        ("Engine load", format_value(state.engine_load_pct, "%")),
        ("MAP", format_value(state.map_kpa, "kPa")),
        ("Barometric", format_value(state.baro_kpa, "kPa")),
        ("Mass airflow", format_value(state.maf_gps, "g/s", 2)),
        ("Fuel level", format_value(state.fuel_level_pct, "%")),
        ("Module voltage", format_value(state.control_voltage, "V", 2)),
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
