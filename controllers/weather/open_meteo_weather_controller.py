"""Open-Meteo weather retrieval independent of any UI toolkit."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Protocol

import requests

from controllers.weather.weather_snapshot import WeatherLocation, WeatherSnapshot
from controllers.weather.weather_snapshot_cache import WeatherSnapshotCache


class WeatherLocationProviderIf(Protocol):
    """Supply coordinates for weather retrieval."""

    def get_location(self) -> WeatherLocation:
        """Return the preferred current location."""
        ...


class OpenMeteoWeatherController:
    """Refresh and cache Open-Meteo forecast snapshots."""

    URL = "https://api.open-meteo.com/v1/forecast"

    def __init__(
        self,
        cache: WeatherSnapshotCache,
        *,
        latitude: float = 42.6709,
        longitude: float = -83.0330,
        location_name: str = "Fallback Location",
        source: str = "Configured location",
        timeout_seconds: float = 10.0,
        session: requests.Session | None = None,
        clock: Callable[[], float] = time.time,
        location_provider: WeatherLocationProviderIf | None = None,
    ) -> None:
        self._cache = cache
        self._latitude = latitude
        self._longitude = longitude
        self._location_name = location_name
        self._source = source
        self._timeout_seconds = timeout_seconds
        self._session = session or requests.Session()
        self._clock = clock
        self._location_provider = location_provider

    def latest(self) -> WeatherSnapshot | None:
        """Return the latest persisted snapshot without network access.

        @return Cached snapshot or None.
        """
        return self._cache.load()

    def refresh(self) -> WeatherSnapshot:
        """Fetch, validate, and persist a fresh forecast.

        @return Newly persisted weather snapshot.
        @exception requests.RequestException if Open-Meteo cannot be reached.
        @exception ValueError if the response does not contain forecast data.
        """
        location = self._resolve_location()
        response = self._session.get(
            self.URL,
            params=self._request_params(location),
            timeout=self._timeout_seconds,
        )
        response.raise_for_status()
        forecast = response.json()
        if not isinstance(forecast, dict) or not all(
            key in forecast for key in ("current", "hourly", "daily")
        ):
            raise ValueError("Open-Meteo returned incomplete forecast data")
        snapshot = WeatherSnapshot(
            latitude=location.latitude,
            longitude=location.longitude,
            location_name=location.name,
            source=location.source,
            fetched_at=self._clock(),
            forecast=forecast,
        )
        self._cache.store(snapshot)
        return snapshot

    def refresh_if_stale(self, max_age_seconds: float) -> WeatherSnapshot:
        """Return cached data when fresh, otherwise request an update.

        If refresh fails and older cached data exists, that stale snapshot is
        returned so consumers retain useful offline behavior.

        @param max_age_seconds Maximum acceptable snapshot age.
        @return Fresh or fallback cached snapshot.
        """
        if max_age_seconds < 0:
            raise ValueError("max_age_seconds cannot be negative")
        cached = self.latest()
        if (
            cached is not None
            and self._clock() - cached.fetched_at <= max_age_seconds
        ):
            return cached
        try:
            return self.refresh()
        except Exception:
            if cached is not None:
                return cached
            raise

    def _resolve_location(self) -> WeatherLocation:
        provider = self._location_provider
        if provider is not None:
            try:
                return provider.get_location()
            except Exception:
                pass
        return WeatherLocation(
            latitude=self._latitude,
            longitude=self._longitude,
            name=self._location_name,
            source=self._source,
        )

    def _request_params(
        self,
        location: WeatherLocation,
    ) -> dict[str, str | float | int]:
        return {
            "latitude": location.latitude,
            "longitude": location.longitude,
            "timezone": "auto",
            "current": ",".join((
                "temperature_2m", "apparent_temperature",
                "relative_humidity_2m", "precipitation", "rain", "showers",
                "snowfall", "weather_code", "cloud_cover", "pressure_msl",
                "surface_pressure", "wind_speed_10m", "wind_direction_10m",
                "wind_gusts_10m",
            )),
            "hourly": ",".join((
                "temperature_2m", "apparent_temperature",
                "precipitation_probability", "precipitation",
                "weather_code", "cloud_cover", "wind_speed_10m",
            )),
            "daily": ",".join((
                "weather_code", "temperature_2m_max", "temperature_2m_min",
                "sunrise", "sunset", "precipitation_probability_max",
                "wind_speed_10m_max",
            )),
            "forecast_days": 7,
        }
