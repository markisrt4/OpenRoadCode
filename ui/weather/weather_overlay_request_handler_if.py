# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Semantic actions emitted by weather map controls."""

from abc import ABC, abstractmethod


class WeatherOverlayRequestHandlerIf(ABC):
    """Accept map-weather intent without exposing controllers or transport."""

    @abstractmethod
    def request_city_enabled(self, enabled: bool) -> None:
        """Set city overlay visibility.

        @param enabled Whether to show city weather.
        """
        ...

    @abstractmethod
    def request_city_selection(self, kind: str, period: str, hours: int) -> None:
        """Select a city field and time window.

        @param kind Temperature, wind or precipitation.
        @param period Past model estimates or future forecasts.
        @param hours Selected hour/window length from 1 to 24.
        """
        ...

    @abstractmethod
    def request_city_playback(self, playing: bool) -> None:
        """Start or pause city playback independently of radar.

        @param playing Whether to animate downloaded hourly values.
        """
        ...

    @abstractmethod
    def request_city_refresh(self) -> None:
        """Request fresh city data."""
        ...

    @abstractmethod
    def request_city_details(self, city_id: str | None) -> None:
        """Open a displayed city's weather details or dismiss the selection.

        @param city_id Displayed city identity, or None to close details.
        """
        ...

    @abstractmethod
    def request_model_selection(self, kind: str) -> None:
        """Choose one model heatmap or turn it off.

        @param kind Off, temperature or wind.
        """
        ...

    @abstractmethod
    def request_model_refresh(self) -> None:
        """Request a fresh full-area forecast."""
        ...

    @abstractmethod
    def request_route_enabled(self, enabled: bool) -> None:
        """Enable weather at estimated route arrival times.

        @param enabled Whether to display route weather.
        """
        ...

    @abstractmethod
    def request_route_layers(self, layers: frozenset[str]) -> None:
        """Choose route checkpoint values.

        @param layers Temperature, rain probability and/or wind.
        """
        ...

    @abstractmethod
    def request_route_refresh(self) -> None:
        """Request fresh forecasts for the remaining route."""
        ...

    @abstractmethod
    def request_navigation_visible(self, visible: bool) -> None:
        """Start or stop navigation-only weather activity.

        @param visible Whether Navigation is currently shown.
        """
        ...

    @abstractmethod
    def request_replay(self) -> None:
        """Replay weather state after a renderer restart."""
        ...
