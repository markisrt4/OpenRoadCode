# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Contract implemented by normalized weather providers."""

from __future__ import annotations

from abc import ABC, abstractmethod

from controllers.weather.weather_state import WeatherLocation, WeatherState


class WeatherProviderIf(ABC):
    """Fetch weather without exposing provider-specific transport details."""

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Return the stable provider identifier."""

    @abstractmethod
    def refresh(self, location: WeatherLocation) -> WeatherState:
        """Fetch and return a fresh normalized weather state."""
