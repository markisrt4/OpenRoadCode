# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Native map adapter for toolkit-independent weather overlay snapshots."""

import math

from ui.weather.weather_overlay_ui_if import WeatherOverlayUiIf
from .weather_overlay_format import weather_value, route_weather_label


class MapWeatherOverlayUi(WeatherOverlayUiIf):
    """Translate SI weather state into renderer-specific GeoJSON and raster commands."""

    def __init__(self, renderer, unit_system):
        self._renderer, self._unit_system = renderer, unit_system

    def set_city_weather_state(self, state):
        features = []
        if state.enabled and state.visible:
            for point in state.points:
                features.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [
                    math.degrees(point.position.longitude_rad), math.degrees(point.position.latitude_rad)]},
                    "properties": {"name": point.name, "weather_city_id": point.city_id,
                                   "value": weather_value(point.value_si, state.kind, self._unit_system().value == "imperial"),
                                   "color": "#f8e58b" if state.kind == "temperature" else
                                            "#a6edff" if state.kind == "wind" else "#a2f2c4"}})
        self._renderer.set_city_weather({"type": "FeatureCollection", "features": features})

    def set_model_weather_state(self, state):
        raster = state.raster
        if raster is None:
            self._renderer.set_weather_field(None, enabled=False)
        else:
            self._renderer.set_weather_field(raster.tile_url, frame_time=raster.frame_time,
                                             max_zoom=raster.max_zoom, opacity=raster.opacity)

    def set_route_weather_state(self, state):
        features = []
        if state.enabled and state.layers:
            for index, point in enumerate(state.points, 1):
                arrival = point.arrival.astimezone().strftime('%I:%M %p').lstrip('0')
                features.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [
                    math.degrees(point.position.longitude_rad), math.degrees(point.position.latitude_rad)]},
                    "properties": {"label": f"{index} · ~{arrival}\n" +
                                   route_weather_label(point, state.layers, self._unit_system().value == "imperial")}})
        self._renderer.set_route_weather({"type": "FeatureCollection", "features": features})
