# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for provider-independent weather orchestration."""

from unittest.mock import Mock

import pytest

from controllers.weather import WeatherController, WeatherLocation
from controllers.weather.weather_state import CurrentWeather, WeatherSource, WeatherState


def _state(*, fetched_at: float, name: str = "Romeo") -> WeatherState:
    return WeatherState(
        latitude=42.8028,
        longitude=-83.0127,
        location_name=name,
        location_source="test",
        source=WeatherSource("test", "Test Weather"),
        fetched_at=fetched_at,
        current=CurrentWeather(),
    )


def test_refresh_uses_location_provider():
    provider = Mock()
    provider.provider_id = "test"
    provider.refresh.return_value = _state(fetched_at=100.0, name="GPS fix")
    location_provider = Mock()
    location_provider.get_location.return_value = WeatherLocation(
        latitude=45.0,
        longitude=-75.0,
        name="GPS fix",
        source="GPSD",
    )
    controller = WeatherController(provider, location_provider=location_provider)

    result = controller.refresh()

    requested = provider.refresh.call_args.args[0]
    assert requested.latitude == 45.0
    assert requested.longitude == -75.0
    assert result.location_name == "GPS fix"
    assert controller.latest() is result


def test_refresh_uses_fallback_when_location_provider_fails():
    provider = Mock()
    provider.provider_id = "test"
    provider.refresh.return_value = _state(fetched_at=100.0)
    location_provider = Mock()
    location_provider.get_location.side_effect = RuntimeError("no fix")
    fallback = WeatherLocation(42.8028, -83.0127, "Fallback", "config")
    controller = WeatherController(
        provider,
        location_provider=location_provider,
        fallback_location=fallback,
    )

    controller.refresh()

    assert provider.refresh.call_args.args[0] == fallback


def test_refresh_if_stale_reuses_fresh_state():
    provider = Mock()
    provider.provider_id = "test"
    provider.refresh.return_value = _state(fetched_at=100.0)
    controller = WeatherController(
        provider,
        fallback_location=WeatherLocation(1.0, 2.0, "Test", "test"),
        clock=lambda: 105.0,
    )

    first = controller.refresh()
    second = controller.refresh_if_stale(10.0)

    assert second is first
    assert provider.refresh.call_count == 1


def test_refresh_if_stale_returns_previous_state_when_refresh_fails():
    provider = Mock()
    provider.provider_id = "test"
    provider.refresh.side_effect = [_state(fetched_at=1.0), RuntimeError("offline")]
    controller = WeatherController(
        provider,
        fallback_location=WeatherLocation(1.0, 2.0, "Test", "test"),
        clock=lambda: 1000.0,
    )

    existing = controller.refresh()
    result = controller.refresh_if_stale(10.0)

    assert result is existing


def test_refresh_requires_a_location():
    provider = Mock()
    provider.provider_id = "test"
    controller = WeatherController(provider)

    with pytest.raises(RuntimeError, match="No weather location"):
        controller.refresh()


def test_negative_stale_age_is_rejected():
    provider = Mock()
    provider.provider_id = "test"
    controller = WeatherController(provider)

    with pytest.raises(ValueError):
        controller.refresh_if_stale(-1.0)
