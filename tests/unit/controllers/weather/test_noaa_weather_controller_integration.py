"""Hardware-free integration tests for optional NOAA source selection."""

from __future__ import annotations

from controllers.weather.weather_controller import WeatherController
from controllers.weather.weather_source_selector import WeatherSourceSelector
from controllers.weather.weather_state import (
    CurrentWeather,
    WeatherLocation,
    WeatherSource,
    WeatherState,
)


class StubProvider:
    def __init__(self, source: str, *, fails: bool = False) -> None:
        self.source = source
        self.fails = fails
        self.calls = 0

    @property
    def provider_id(self) -> str:
        return self.source

    def refresh(self, location: WeatherLocation) -> WeatherState:
        self.calls += 1
        if self.fails:
            raise RuntimeError("unavailable")
        return WeatherState(
            latitude=location.latitude,
            longitude=location.longitude,
            location_name=location.name,
            location_source=location.source,
            source=WeatherSource(self.source, self.source),
            fetched_at=100.0,
            current=CurrentWeather(),
        )


LOCATION = WeatherLocation(42.8, -83.0, "Romeo", "test")


def test_opt_in_offline_controller_uses_rf():
    online = StubProvider("online")
    rf = StubProvider("noaa_rf")
    controller = WeatherController(
        online,
        fallback_location=LOCATION,
        network_allowed=lambda: False,
        source_selector=WeatherSourceSelector(online, rf, clock=lambda: 101.0),
    )
    assert controller.refresh().source.provider_id == "noaa_rf"
    assert online.calls == 0
    assert rf.calls == 1


def test_opt_in_online_controller_prefers_online():
    online = StubProvider("online")
    rf = StubProvider("noaa_rf")
    controller = WeatherController(
        online,
        fallback_location=LOCATION,
        source_selector=WeatherSourceSelector(online, rf, clock=lambda: 101.0),
    )
    assert controller.refresh().source.provider_id == "online"
    assert rf.calls == 0


def test_opt_in_controller_retains_cache_when_sources_fail():
    online = StubProvider("online")
    rf = StubProvider("noaa_rf")
    controller = WeatherController(
        online,
        fallback_location=LOCATION,
        network_allowed=lambda: False,
        source_selector=WeatherSourceSelector(online, rf, clock=lambda: 101.0),
    )
    previous = controller.refresh()
    rf.fails = True
    assert controller.refresh() is previous


def test_default_controller_offline_behavior_unchanged():
    online = StubProvider("online")
    controller = WeatherController(
        online,
        fallback_location=LOCATION,
        network_allowed=lambda: False,
    )
    import pytest

    with pytest.raises(RuntimeError, match="Offline mode"):
        controller.refresh()
    assert online.calls == 0
