"""Hardware-free NOAA RF provider contract tests."""

from __future__ import annotations

import pytest

from controllers.weather.noaa_forecast_store import NoaaForecastStore
from controllers.weather.noaa_rf_weather_provider import NoaaRfWeatherProvider
from controllers.weather.weather_provider_if import WeatherProviderIf
from controllers.weather.weather_state import WeatherLocation


def forecast(area="Macomb County", *, boundary=False):
    return {
        "event": "noaa_forecast_completed",
        "forecast_area": area,
        "forecast_areas": [area] if area else [],
        "forecast_cycle": 1,
        "forecast_revision": 2,
        "cycle_boundary_suspected": boundary,
        "completed_forecast": {"forecast": {
            "period": "tonight",
            "conditions": "mostly cloudy",
            "low_f": 32,
            "high_f": None,
            "precipitation_chance_percent": 40,
        }},
    }


def location():
    return WeatherLocation(42.8, -83.0, "Romeo", "test")


def test_verified_area_maps_named_period_without_inventing_current_conditions():
    store = NoaaForecastStore(clock=lambda: 100.0)
    store.ingest(forecast())
    provider = NoaaRfWeatherProvider(
        store, area_matches=lambda area, loc: area == "Macomb County",
        clock=lambda: 110.0,
    )
    assert isinstance(provider, WeatherProviderIf)
    state = provider.refresh(location())
    assert state.source.provider_id == "noaa_rf"
    assert state.fetched_at == 100.0
    assert state.current.temperature_k is None
    assert state.daily == ()
    assert state.text_periods[0].label == "tonight"
    assert state.text_periods[0].temperature_low_k == pytest.approx(273.15)
    assert state.text_periods[0].precipitation_probability == pytest.approx(0.4)


@pytest.mark.parametrize("area,boundary,matched,now", [
    (None, False, True, 110.0),
    ("Other County", False, False, 110.0),
    ("Macomb County", True, True, 110.0),
    ("Macomb County", False, True, 4000.0),
])
def test_rejects_unverified_or_stale_forecast(area, boundary, matched, now):
    store = NoaaForecastStore(clock=lambda: 100.0)
    store.ingest(forecast(area, boundary=boundary))
    provider = NoaaRfWeatherProvider(
        store, area_matches=lambda _area, _location: matched,
        clock=lambda: now,
    )
    with pytest.raises(RuntimeError):
        provider.refresh(location())


def test_missing_forecast_rejected():
    provider = NoaaRfWeatherProvider(
        NoaaForecastStore(), area_matches=lambda _area, _location: True
    )
    with pytest.raises(RuntimeError, match="No NOAA RF forecast"):
        provider.refresh(location())
