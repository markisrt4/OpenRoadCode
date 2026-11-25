# SPDX-License-Identifier: MIT
"""Convert SDRForge tracker/simulation records to ORC's immutable SI UI contract."""

from dataclasses import asdict, is_dataclass
from math import radians

from ui.adsb.aircraft_overlay_state import AircraftPoint
from ui.navigation.map_ui_if import GeoPoint


def aircraft_from_snapshot(snapshot):
    """Accept dictionaries or SDRForge Aircraft dataclasses; no SDRForge import."""
    result = []
    for raw in snapshot:
        item = asdict(raw) if is_dataclass(raw) else raw
        lat, lon = item.get("latitude"), item.get("longitude")
        position = None
        if lat is not None and lon is not None:
            position = GeoPoint(
                radians(lat),
                radians(lon),
                item["altitude_ft"] * 0.3048 if item.get("altitude_ft") is not None else None,
            )
        result.append(
            AircraftPoint(
                icao=item["icao"],
                position=position,
                callsign=item.get("callsign"),
                speed_m_s=item["speed_kt"] * 1852 / 3600
                if item.get("speed_kt") is not None
                else None,
                heading_rad=radians(item["heading_deg"])
                if item.get("heading_deg") is not None
                else None,
                vertical_speed_m_s=item["vertical_rate_fpm"] * 0.3048 / 60
                if item.get("vertical_rate_fpm") is not None
                else None,
                last_seen=item.get("last_seen"),
            )
        )
    return tuple(result)
