# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Arrival-time forecasts sampled along an active route."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import math

import requests

from controllers.route_planning.route_planning_types import GeoPoint, RouteResult
from controllers.weather.providers.open_meteo_weather_provider import OpenMeteoWeatherProvider


@dataclass(frozen=True)
class RouteCheckpoint:
    point: GeoPoint
    arrival: datetime
    distance_m: float


@dataclass(frozen=True)
class RouteWeather:
    checkpoint: RouteCheckpoint
    temperature_c: float | None
    rain_probability: float | None
    wind_kmh: float | None
    condition: str


def sample_route(route: RouteResult, departure: datetime, progress: float = 0) -> tuple[RouteCheckpoint, ...]:
    """Sample up to six remaining checkpoints using maneuver travel times.

    Progress is a fraction of total route distance. Arrival times are estimates
    from the calculated route, without live traffic or planned stops.
    """
    if not route.shape or not math.isfinite(route.duration_seconds) or route.duration_seconds < 0:
        raise ValueError("Route has no usable geometry or travel time")
    distances = [0.0]
    for a, b in zip(route.shape, route.shape[1:]):
        lat1, lat2 = math.radians(a.latitude), math.radians(b.latitude)
        angle = (math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2)
                 * math.sin(math.radians(b.longitude - a.longitude) / 2) ** 2)
        distances.append(distances[-1] + 6371000 * 2 * math.asin(math.sqrt(min(1, angle))))
    total = distances[-1]
    if not total:
        return (RouteCheckpoint(route.shape[-1], departure, 0),)
    # Use maneuver durations where the provider supplies complete, contiguous
    # shape coverage; otherwise explicitly use distance-proportional estimates.
    times = [route.duration_seconds * value / total for value in distances]
    maneuvers = route.maneuvers
    valid = bool(maneuvers) and maneuvers[0].begin_shape_index == 0
    end = 0
    elapsed = 0.0
    for maneuver in maneuvers:
        begin, finish = maneuver.begin_shape_index, maneuver.end_shape_index
        if (begin != end or not begin <= finish < len(distances)
                or not math.isfinite(maneuver.duration_seconds) or maneuver.duration_seconds < 0):
            valid = False
            break
        length = distances[finish] - distances[begin]
        for index in range(begin, finish + 1):
            ratio = (distances[index] - distances[begin]) / length if length else 0
            times[index] = elapsed + ratio * maneuver.duration_seconds
        elapsed += maneuver.duration_seconds
        end = finish
    if not valid or end != len(distances) - 1 or elapsed <= 0:
        times = [route.duration_seconds * value / total for value in distances]
    else:
        times = [value * route.duration_seconds / elapsed for value in times]

    def interpolate(distance):
        index = next((i for i in range(1, len(distances)) if distances[i] >= distance), len(distances) - 1)
        start, finish = route.shape[index - 1:index + 1]
        span = distances[index] - distances[index - 1]
        ratio = (distance - distances[index - 1]) / span if span else 0
        delta_lon = (finish.longitude - start.longitude + 180) % 360 - 180
        point = GeoPoint(start.latitude + ratio * (finish.latitude - start.latitude),
                         (start.longitude + ratio * delta_lon + 180) % 360 - 180)
        return point, times[index - 1] + ratio * (times[index] - times[index - 1])

    progress = max(0, min(1, progress))
    start_distance = total * progress
    _, start_time = interpolate(start_distance)
    count = min(6, max(2, math.ceil((total - start_distance) / 50000) + 1))
    result = []
    for index in range(count):
        distance = start_distance + (total - start_distance) * index / (count - 1)
        point, seconds = interpolate(distance)
        result.append(RouteCheckpoint(point, departure + timedelta(seconds=seconds - start_time),
                                      distance - start_distance))
    return tuple(result)


class RouteWeatherProvider:
    """Fetch a single batch of hourly forecasts in UTC for route checkpoints."""

    def __init__(self, session=None):
        self._session = session or requests.Session()

    def close(self) -> None:
        """Release pooled forecast connections."""
        self._session.close()

    def forecast(self, checkpoints: tuple[RouteCheckpoint, ...]) -> tuple[RouteWeather, ...]:
        if not checkpoints:
            return ()
        response = self._session.get(OpenMeteoWeatherProvider.URL, params={
            "latitude": ",".join(str(c.point.latitude) for c in checkpoints),
            "longitude": ",".join(str(c.point.longitude) for c in checkpoints),
            "hourly": "temperature_2m,precipitation_probability,wind_speed_10m,weather_code",
            "timezone": "UTC", "timeformat": "unixtime", "forecast_days": 7,
            "temperature_unit": "celsius", "wind_speed_unit": "kmh",
        }, timeout=15)
        response.raise_for_status()
        payload = response.json()
        locations = payload if isinstance(payload, list) else [payload]
        if len(locations) != len(checkpoints):
            raise ValueError("Route forecast returned an unexpected number of locations")
        results = []
        for checkpoint, location in zip(checkpoints, locations):
            hourly = location.get("hourly", {})
            times = hourly.get("time", [])
            if not times:
                raise ValueError("Route forecast has no hourly data")
            arrival = checkpoint.arrival.astimezone(timezone.utc).timestamp()
            index = min(range(len(times)), key=lambda i: abs(times[i] - arrival))
            if abs(times[index] - arrival) > 3600:
                raise ValueError("Route arrival is outside the available hourly forecast")

            def value(key, low, high):
                values = hourly.get(key, [])
                item = values[index] if index < len(values) else None
                return item if isinstance(item, (float, int)) and math.isfinite(item) and low <= item <= high else None

            code = value("weather_code", 0, 99)
            results.append(RouteWeather(checkpoint, value("temperature_2m", -100, 70),
                                        value("precipitation_probability", 0, 100),
                                        value("wind_speed_10m", 0, 500),
                                        OpenMeteoWeatherProvider._condition(code).value.replace("_", " ")))
        return tuple(results)
