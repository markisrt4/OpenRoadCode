# SPDX-License-Identifier: MIT
"""Convert SDRForge aircraft snapshots into independent map overlay features.

This is a transport-agnostic presentation model. It does not alter the route,
camera, weather layers, or existing ADS-B browser lifecycle.
"""
from __future__ import annotations

from math import isfinite
from typing import Iterable, Mapping


def aircraft_geojson(aircraft: Iterable[Mapping[str, object]]) -> dict[str, object]:
    """Create a GeoJSON FeatureCollection for aircraft with valid positions.

    Input fields follow SDRForge AircraftTracker snapshots. Aircraft without
    decoded positions are omitted rather than plotted at arbitrary coordinates.
    """
    features = []
    for item in aircraft:
        lat, lon = item.get("latitude"), item.get("longitude")
        if not isinstance(lat, (int, float)) or isinstance(lat, bool):
            continue
        if not isinstance(lon, (int, float)) or isinstance(lon, bool):
            continue
        if not (isfinite(lat) and isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180):
            continue
        icao = item.get("icao")
        if not isinstance(icao, str) or len(icao) != 6:
            continue
        props = {"icao": icao.upper()}
        for name in ("callsign", "altitude_ft", "speed_kt", "heading_deg",
                     "vertical_rate_fpm", "last_seen"):
            value = item.get(name)
            if value is not None:
                props[name] = value
        features.append({
            "type": "Feature",
            "id": icao.upper(),
            "geometry": {"type": "Point", "coordinates": [float(lon), float(lat)]},
            "properties": props,
        })
    return {"type": "FeatureCollection", "features": features}
