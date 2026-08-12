# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Compose live GPSD and cached-position weather location selection."""

from datetime import datetime

from controllers.navigation import PositionSnapshotCache
from controllers.weather import GpsdWeatherLocationProvider, WeatherLocation


class CarUiWeatherLocationProvider:
    """Prefer live GPSD and fall back to a recent persisted position."""

    def __init__(
        self,
        gpsd: GpsdWeatherLocationProvider,
        position_cache: PositionSnapshotCache,
        *,
        max_age_seconds: float = 604800.0,
    ) -> None:
        self._gpsd = gpsd
        self._position_cache = position_cache
        self._max_age_seconds = max_age_seconds

    def get_location(self) -> WeatherLocation:
        """Return live GPSD coordinates or a recent cached fix."""
        try:
            return self._gpsd.get_location()
        except Exception as live_error:
            cached = self._position_cache.load()
            if cached is None:
                raise RuntimeError("No live or cached position") from live_error
            age = (datetime.now() - cached.received_at).total_seconds()
            if age < 0 or age > self._max_age_seconds:
                raise RuntimeError("Cached position is expired") from live_error
            assert cached.latitude_deg is not None
            assert cached.longitude_deg is not None
            return WeatherLocation(
                latitude=cached.latitude_deg,
                longitude=cached.longitude_deg,
                name=(
                    f"{cached.latitude_deg:.5f}, "
                    f"{cached.longitude_deg:.5f}"
                ),
                source="Last known position",
            )
