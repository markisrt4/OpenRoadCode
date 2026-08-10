"""Reusable curses presentation for navigation snapshots."""

from __future__ import annotations

import curses
import math
from typing import Protocol

from frontends.tui.curses_helpers import addstr, format_value


ACCELERATION_MODES = ("raw", "linear", "both")


class VectorSnapshot(Protocol):
    x: float
    y: float
    z: float


class PositionSnapshot(Protocol):
    latitude_deg: float | None
    longitude_deg: float | None
    altitude_m: float | None
    speed_mps: float | None
    course_deg: float | None
    fix_mode: int | None
    satellites_used: int | None

    @property
    def has_fix(self) -> bool: ...


class NavigationSnapshot(Protocol):
    timestamp: object
    heading_deg: float
    pitch_deg: float
    roll_deg: float
    acceleration_mps2: VectorSnapshot
    linear_acceleration_mps2: VectorSnapshot
    angular_velocity_rad_s: VectorSnapshot
    gps: PositionSnapshot | None


def navigation_fields(
    state: NavigationSnapshot | None,
    gps_enabled: bool,
    acceleration_mode: str = "both",
) -> tuple[tuple[str, str], ...]:
    """Return formatted labels and values for a navigation snapshot."""
    if acceleration_mode not in ACCELERATION_MODES:
        raise ValueError(f"invalid acceleration mode: {acceleration_mode}")
    fields: list[tuple[str, str]] = []
    if state is None:
        fields.extend((label, "--") for label in ("Heading", "Pitch", "Roll"))
    else:
        fields.extend((
            ("Heading", format_value(state.heading_deg, "°", 2)),
            ("Pitch", format_value(state.pitch_deg, "°", 2)),
            ("Roll", format_value(state.roll_deg, "°", 2)),
        ))
    if acceleration_mode in ("raw", "both"):
        fields.extend(_acceleration_fields(
            state.acceleration_mps2 if state is not None else None,
            "Raw accel",
        ))
    if acceleration_mode in ("linear", "both"):
        fields.extend(_acceleration_fields(
            state.linear_acceleration_mps2 if state is not None else None,
            "Linear accel",
        ))
    angular = state.angular_velocity_rad_s if state is not None else None
    for axis in ("X", "Y", "Z"):
        value = getattr(angular, axis.lower()) if angular is not None else None
        fields.append((f"Angular velocity {axis}", format_value(value, "rad/s", 4)))
    if not gps_enabled:
        return tuple(fields)
    gps = state.gps if state is not None else None
    fields.extend((
        ("GPS fix", f"{gps.fix_mode}D" if gps is not None and gps.has_fix else "Waiting"),
        ("Latitude", format_value(gps.latitude_deg if gps else None, "°", 6)),
        ("Longitude", format_value(gps.longitude_deg if gps else None, "°", 6)),
        ("Altitude", format_value(gps.altitude_m if gps else None, "m", 1)),
        ("Ground speed", format_value(gps.speed_mps if gps else None, "m/s", 2)),
        ("Course over ground", format_value(gps.course_deg if gps else None, "°", 1)),
        ("Satellites", str(gps.satellites_used) if gps and gps.satellites_used is not None else "--"),
    ))
    return tuple(fields)


def _acceleration_fields(
    acceleration: VectorSnapshot | None,
    label_prefix: str,
) -> tuple[tuple[str, str], ...]:
    if acceleration is None:
        return tuple((f"{label_prefix} {axis}", "--") for axis in ("X", "Y", "Z", "total"))
    total = math.sqrt(acceleration.x**2 + acceleration.y**2 + acceleration.z**2)
    return (
        (f"{label_prefix} X", format_value(acceleration.x, "m/s²", 3)),
        (f"{label_prefix} Y", format_value(acceleration.y, "m/s²", 3)),
        (f"{label_prefix} Z", format_value(acceleration.z, "m/s²", 3)),
        (f"{label_prefix} total", format_value(total, "m/s²", 3)),
    )


class NavigationDashboardView:
    """Render navigation snapshots into a curses window."""

    def render(
        self,
        screen,
        state: NavigationSnapshot | None,
        status: str,
        connected: bool,
        gps_enabled: bool,
        acceleration_mode: str,
        controls: str | None = None,
    ) -> None:
        screen.erase()
        height, width = screen.getmaxyx()
        title_attr = curses.A_BOLD | (curses.color_pair(1) if curses.has_colors() else 0)
        addstr(screen, 0, 2, "OpenRoadCode Navigation", title_attr)
        addstr(screen, 1, 0, "─" * max(0, width - 1))
        connection = "CONNECTED" if connected else "DISCONNECTED"
        connection_attr = curses.A_BOLD | (
            curses.color_pair(2 if connected else 3) if curses.has_colors() else 0
        )
        addstr(screen, 2, 2, connection, connection_attr)
        if state is not None:
            timestamp = getattr(state.timestamp, "strftime", lambda _fmt: "--:--:--")
            addstr(screen, 2, max(24, width - 24), f"Updated {timestamp('%H:%M:%S')}")
        fields = navigation_fields(state, gps_enabled, acceleration_mode)
        two_columns = width >= 84
        rows_per_column = (len(fields) + 1) // 2 if two_columns else len(fields)
        column_width = width // 2 if two_columns else width
        for index, (label, value) in enumerate(fields):
            column_index = index // rows_per_column if two_columns else 0
            row = 4 + index % rows_per_column
            column = 2 + column_index * column_width
            addstr(screen, row, column, f"{label:<21}", curses.A_DIM)
            addstr(screen, row, column + 22, value, curses.A_BOLD)
        footer_row = min(height - 3, 5 + rows_per_column)
        addstr(screen, footer_row, 0, "─" * max(0, width - 1))
        addstr(screen, footer_row + 1, 2, status)
        controls = controls or f"q: quit   h: reset   c: calibrate   a: acceleration ({acceleration_mode})"
        addstr(screen, height - 1, max(2, width - len(controls) - 2), controls)
        screen.refresh()
