# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Provider-independent weather orchestration."""

from __future__ import annotations

import logging

from collections.abc import Callable
import time
from typing import Protocol

from controllers.weather.weather_provider_if import WeatherProviderIf
from controllers.weather.weather_state import WeatherLocation, WeatherState
from controllers.weather.weather_logging import WeatherLog
from common.logging.structured import current_operation, operation


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
        network_allowed: Callable[[], bool] = lambda: True,
    ) -> None:
        self._network_allowed = network_allowed
        self._provider = provider
        self._location_provider = location_provider
        self._fallback_location = fallback_location
        self._clock = clock
        self._last_state: WeatherState | None = None
        self._log = WeatherLog("weather.forecast")

    @property
    def provider_id(self) -> str:
        return self._provider.provider_id

    def latest(self) -> WeatherState | None:
        return self._last_state

    def refresh(self) -> WeatherState:
        operation_id = self._log.requested()
        if not self._network_allowed():
            if self._last_state is not None:
                self._log.emit(logging.DEBUG, "weather.cache_used", "Offline weather cache used", operation_id)
                return self._last_state
            self._log.failed(operation_id=operation_id, reason="offline_without_cache")
            raise RuntimeError("Offline mode: no cached weather available")
        with operation(operation_id):
            try:
                location = self._resolve_location()
                state = self._provider.refresh(location)
            except Exception as error:
                self._log.failed(error, operation_id)
                raise
        self._last_state = state
        self._log.succeeded(operation_id)
        return state

    def refresh_if_stale(self, max_age_seconds: float) -> WeatherState:
        if max_age_seconds < 0:
            raise ValueError("max_age_seconds cannot be negative")
        cached = self._last_state
        if cached is not None and self._clock() - cached.fetched_at <= max_age_seconds:
            self._log.emit(logging.DEBUG, "weather.cache_used", "Fresh weather cache used")
            return cached
        with operation(current_operation()):
            try:
                return self.refresh()
            except Exception:
                if cached is not None:
                    self._log.emit(logging.DEBUG, "weather.cache_used", "Previous weather cache used after failure")
                    return cached
                raise

    def _resolve_location(self) -> WeatherLocation:
        if self._location_provider is not None:
            try:
                location = self._location_provider.get_location()
                self._log.succeeded(stage="location")
                return location
            except Exception as error:
                self._log.failed(error, stage="location")
                pass
        # Reuse the last resolved position when GPS is temporarily unavailable.
        if self._last_state is not None:
            cached = self._last_state
            return WeatherLocation(cached.latitude, cached.longitude,
                                   cached.location_name, cached.location_source)
        if self._fallback_location is None:
            raise RuntimeError("No weather location is available")
        return self._fallback_location
