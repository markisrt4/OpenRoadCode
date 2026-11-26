# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Optional NOAA RF weather composition with explicit ownership."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from time import time

from controllers.weather.noaa_forecast_store import NoaaForecastSnapshot, NoaaForecastStore
from controllers.weather.noaa_rf_weather_provider import NoaaRfWeatherProvider
from controllers.weather.noaa_weather_event_adapter import NoaaWeatherEventAdapter
from controllers.weather.noaa_zmq_forecast_subscriber import NoaaZmqForecastSubscriber
from controllers.weather.weather_controller import WeatherController
from controllers.weather.weather_provider_if import WeatherProviderIf
from controllers.weather.weather_source_selector import WeatherSourceSelector
from controllers.weather.weather_state import WeatherLocation


@dataclass(frozen=True, slots=True)
class NoaaRfWeatherPreview:
    """Raw RF weather presentation, even when the forecast area is unknown."""

    period: str
    conditions: str | None
    area: str | None
    frequency_hz: int | None
    received_at: float
    reception_age_seconds: float
    geographically_scoped: bool
    high_f: float | None = None
    low_f: float | None = None
    precipitation_chance_percent: float | None = None
    location_verified: bool = False


class NoaaRfWeatherService:
    """Own the NOAA subscriber, store, provider, and optional controller wiring."""

    def __init__(
        self,
        online_provider: WeatherProviderIf,
        *,
        area_matches: Callable[[str, WeatherLocation], bool],
        endpoint: str = "tcp://127.0.0.1:5573",
        clock: Callable[[], float] = time,
        subscriber_factory: Callable[[NoaaWeatherEventAdapter], NoaaZmqForecastSubscriber]
        | None = None,
    ) -> None:
        self.store = NoaaForecastStore(clock=clock)
        self.adapter = NoaaWeatherEventAdapter(self.store)
        self.provider = NoaaRfWeatherProvider(
            self.store, area_matches=area_matches, clock=clock
        )
        self.selector = WeatherSourceSelector(
            online_provider, self.provider, clock=clock
        )
        self.subscriber = (
            subscriber_factory(self.adapter)
            if subscriber_factory is not None
            else NoaaZmqForecastSubscriber(self.adapter, endpoint=endpoint)
        )
        self._online_provider = online_provider
        self._clock = clock
        self._area_matches = area_matches

    def start(self) -> None:
        """Begin listening; absence of SDR hardware does not block startup."""
        self.subscriber.start()

    def stop(self) -> None:
        """Stop listening and release the subscriber's socket."""
        self.subscriber.stop()

    def preview(self, location: WeatherLocation | None = None) -> NoaaRfWeatherPreview | None:
        """Expose the latest broadcast without claiming that it is local."""
        snapshot: NoaaForecastSnapshot | None = self.store.latest()
        if snapshot is None:
            return None
        return NoaaRfWeatherPreview(
            period=snapshot.period,
            conditions=snapshot.conditions,
            area=snapshot.area,
            frequency_hz=snapshot.frequency_hz,
            received_at=snapshot.received_at,
            reception_age_seconds=max(0.0, self._clock() - snapshot.received_at),
            geographically_scoped=snapshot.geographically_scoped,
            high_f=snapshot.high_f,
            low_f=snapshot.low_f,
            precipitation_chance_percent=snapshot.precipitation_chance_percent,
            location_verified=(
                location is not None
                and snapshot.area is not None
                and self._area_matches(snapshot.area, location)
            ),
        )

    def make_controller(self, **kwargs: object) -> WeatherController:
        """Create a controller with explicit RF source selection enabled."""
        return WeatherController(
            self._online_provider, source_selector=self.selector, **kwargs
        )
