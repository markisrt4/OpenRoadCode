# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Provider-independent weather orchestration."""

from __future__ import annotations

from collections.abc import Callable
import time
from typing import Protocol

from controllers.weather.weather_provider_if import WeatherProviderIf
from controllers.weather.weather_state import WeatherLocation, WeatherState


class WeatherLocationProviderIf(Protocol):
    def get_location(self) -> WeatherLocation: ...


class WeatherController:
    """Resolve location, select provider, and retain the latest weather state."""

    def __init__(
        self,
        provider: WeatherProviderIf,
        *,
        location_provider: WeatherLocationProviderIf | None = None,
        fallback_location: WeatherLocation | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._provider = provider
        self._location_provider = location_provider
        self._fallback_location = fallback_location
        self._clock = clock
        self._last_state: WeatherState | None = None

    @property
    def provider_id(self) -> str:
        return self._provider.provider_id

    def latest(self) -> WeatherState | None:
        return self._last_state

    def refresh(self) -> WeatherState:
        location = self._resolve_location()
        state = self._provider.refresh(location)
        self._last_state = state
        return state

    def refresh_if_stale(self, max_age_seconds: float) -> WeatherState:
        if max_age_seconds < 0:
            raise ValueError("max_age_seconds cannot be negative")
        cached = self._last_state
        if cached is not None and self._clock() - cached.fetched_at <= max_age_seconds:
            return cached
        try:
            return self.refresh()
        except Exception:
            if cached is not None:
                return cached
            raise

    def _resolve_location(self) -> WeatherLocation:
        if self._location_provider is not None:
            try:
                return self._location_provider.get_location()
            except Exception:
                pass
        if self._fallback_location is None:
            raise RuntimeError("No weather location is available")
        return self._fallback_location
