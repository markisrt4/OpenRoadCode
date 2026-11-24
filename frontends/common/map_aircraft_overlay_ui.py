# SPDX-License-Identifier: MIT
"""Native map presentation adapter for aircraft overlay snapshots."""

from math import degrees, isfinite
from ui.adsb.aircraft_overlay_ui_if import AircraftOverlayUiIf


class MapAircraftOverlayUi(AircraftOverlayUiIf):
    def __init__(self, renderer):
        self._renderer = renderer

    def set_aircraft_overlay_state(self, state):
        features = []
        if state.enabled:
            for aircraft in state.aircraft:
                point = aircraft.position
                if point is None:
                    continue
                latitude = degrees(point.latitude_rad)
                longitude = degrees(point.longitude_rad)
                if not (
                    isfinite(latitude)
                    and isfinite(longitude)
                    and -90 <= latitude <= 90
                    and -180 <= longitude <= 180
                ):
                    continue
                props = {"icao": aircraft.icao.upper()}
                if aircraft.callsign:
                    props["callsign"] = aircraft.callsign
                if aircraft.heading_rad is not None and isfinite(aircraft.heading_rad):
                    props["heading_deg"] = degrees(aircraft.heading_rad) % 360
                if point.altitude_m is not None and isfinite(point.altitude_m):
                    props["altitude_ft"] = point.altitude_m / 0.3048
                if aircraft.speed_m_s is not None and isfinite(aircraft.speed_m_s):
                    props["speed_kt"] = aircraft.speed_m_s / (1852 / 3600)
                if aircraft.vertical_speed_m_s is not None and isfinite(
                    aircraft.vertical_speed_m_s
                ):
                    props["vertical_rate_fpm"] = aircraft.vertical_speed_m_s * 60 / 0.3048
                if aircraft.last_seen is not None and isfinite(aircraft.last_seen):
                    props["last_seen"] = aircraft.last_seen
                features.append(
                    {
                        "type": "Feature",
                        "id": aircraft.icao.upper(),
                        "geometry": {"type": "Point", "coordinates": [longitude, latitude]},
                        "properties": props,
                    }
                )
        self._renderer.set_aircraft({"type": "FeatureCollection", "features": features})
