# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Select online weather, verified NOAA RF, or cached weather."""

from __future__ import annotations

from collections.abc import Callable
from time import time

from controllers.weather.weather_provider_if import WeatherProviderIf
from controllers.weather.weather_state import WeatherLocation, WeatherState


class WeatherSourceSelector:
    """Prefer a fresh online forecast; use verified RF only when needed."""

    def __init__(
        self,
        online: WeatherProviderIf,
        rf: WeatherProviderIf,
        *,
        online_max_age_seconds: float = 1800.0,
        clock: Callable[[], float] = time,
    ) -> None:
        if online_max_age_seconds <= 0:
            raise ValueError("online_max_age_seconds must be positive")
        self._online = online
        self._rf = rf
        self._max_age = online_max_age_seconds
        self._clock = clock

    def select(
        self,
        location: WeatherLocation,
        *,
        network_allowed: bool,
        cached: WeatherState | None = None,
    ) -> WeatherState:
        """Return the best available source without falsely claiming RF locality."""
        if network_allowed:
            try:
                online = self._online.refresh(location)
                age = self._clock() - online.fetched_at
                if 0 <= age <= self._max_age:
                    return online
            except (OSError, RuntimeError, ValueError):
                pass
        try:
            return self._rf.refresh(location)
        except (OSError, RuntimeError, ValueError):
            if cached is not None:
                return cached
            raise RuntimeError("No eligible online, NOAA RF, or cached weather") from None
