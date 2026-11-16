# SPDX-License-Identifier: MIT
"""Deterministic, hardware-free aircraft movement for component testing."""
from math import cos, radians, sin, pi
from ui.adsb.aircraft_overlay_state import AircraftPoint
from ui.navigation.map_ui_if import GeoPoint

EARTH_RADIUS_M = 6371000.0


def simulated_aircraft(elapsed_s, count=10, *, center_lat=42.5, center_lon=-83.0):
    """Generate a reproducible snapshot of aircraft circling a test location."""
    if count < 0:
        raise ValueError("aircraft count must be nonnegative")
    results = []
    for index in range(count):
        angle = (2 * pi * index / max(count, 1)) + elapsed_s * (0.004 + index * 0.0002)
        radius = 12000.0 + index * 2500.0
        north = radius * cos(angle)
        east = radius * sin(angle)
        lat = radians(center_lat) + north / EARTH_RADIUS_M
        lon = radians(center_lon) + east / (EARTH_RADIUS_M * cos(radians(center_lat)))
        heading = (angle + pi / 2) % (2 * pi)
        results.append(AircraftPoint(
            icao=f"{0xA00000 + index:06X}",
            position=GeoPoint(lat, lon, 1500.0 + index * 300),
            callsign=f"TEST{index + 1:03d}",
            speed_m_s=80.0 + index * 5,
            heading_rad=heading,
            last_seen=elapsed_s,
        ))
    return tuple(results)
