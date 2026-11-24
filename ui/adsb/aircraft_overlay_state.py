# SPDX-License-Identifier: MIT
"""Immutable, SI-unit aircraft presentation state."""

from dataclasses import dataclass
from ui.navigation.map_ui_if import GeoPoint


@dataclass(frozen=True, slots=True)
class AircraftPoint:
    icao: str
    position: GeoPoint | None = None
    callsign: str | None = None
    speed_m_s: float | None = None
    heading_rad: float | None = None
    vertical_speed_m_s: float | None = None
    last_seen: float | None = None


@dataclass(frozen=True, slots=True)
class AircraftOverlayState:
    enabled: bool = False
    aircraft: tuple[AircraftPoint, ...] = ()
    selected_icao: str | None = None
    follow_icao: str | None = None
    status: str = ""
