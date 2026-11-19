"""Hardware-free weather source selection tests."""

from __future__ import annotations

import pytest

from controllers.weather.weather_source_selector import WeatherSourceSelector
from controllers.weather.weather_state import (
    CurrentWeather,
    WeatherLocation,
    WeatherSource,
    WeatherState,
)


class StubProvider:
    def __init__(self, result):
        self.result = result
        self.calls = 0

    @property
    def provider_id(self):
        return "stub"

    def refresh(self, location):
        self.calls += 1
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def state(provider_id, fetched_at=100.0):
    return WeatherState(
        latitude=42.8,
        longitude=-83.0,
        location_name="Romeo",
        location_source="test",
        source=WeatherSource(provider_id, provider_id),
        fetched_at=fetched_at,
        current=CurrentWeather(),
    )


def location():
    return WeatherLocation(42.8, -83.0, "Romeo", "test")


def test_fresh_online_wins_without_querying_rf():
    online = StubProvider(state("online"))
    rf = StubProvider(state("noaa_rf"))
    selector = WeatherSourceSelector(online, rf, clock=lambda: 101.0)
    assert selector.select(location(), network_allowed=True).source.provider_id == "online"
    assert rf.calls == 0


def test_offline_uses_rf_before_cache():
    online = StubProvider(state("online"))
    rf = StubProvider(state("noaa_rf"))
    selector = WeatherSourceSelector(online, rf)
    result = selector.select(
        location(), network_allowed=False, cached=state("cache")
    )
    assert result.source.provider_id == "noaa_rf"
    assert online.calls == 0


def test_online_failure_falls_back_to_rf():
    selector = WeatherSourceSelector(
        StubProvider(OSError("offline")),
        StubProvider(state("noaa_rf")),
    )
    assert selector.select(location(), network_allowed=True).source.provider_id == "noaa_rf"


def test_stale_online_falls_back_to_rf():
    selector = WeatherSourceSelector(
        StubProvider(state("online", fetched_at=1.0)),
        StubProvider(state("noaa_rf")),
        clock=lambda: 4000.0,
    )
    assert selector.select(location(), network_allowed=True).source.provider_id == "noaa_rf"


def test_cache_used_when_both_unavailable():
    selector = WeatherSourceSelector(
        StubProvider(RuntimeError("network")),
        StubProvider(RuntimeError("RF area unknown")),
    )
    cached = state("cache")
    assert selector.select(location(), network_allowed=True, cached=cached) is cached


def test_no_sources_raises():
    selector = WeatherSourceSelector(
        StubProvider(RuntimeError("network")),
        StubProvider(RuntimeError("RF area unknown")),
    )
    with pytest.raises(RuntimeError, match="No eligible"):
        selector.select(location(), network_allowed=False)
