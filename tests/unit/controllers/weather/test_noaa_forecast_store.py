"""Hardware-free tests for NOAA forecast storage."""

from __future__ import annotations

import pytest

from controllers.weather.noaa_forecast_store import NoaaForecastStore


def event(*, area="Macomb County", period="tonight"):
    return {
        "event": "noaa_forecast_completed",
        "forecast_area": area,
        "forecast_areas": [area] if area else [],
        "source_frequency_hz": 162550000,
        "forecast_cycle": 0,
        "forecast_revision": 1,
        "cycle_boundary_suspected": False,
        "completed_forecast": {
            "forecast": {
                "period": period,
                "conditions": "mostly cloudy",
                "high_f": None,
                "low_f": 42,
                "precipitation_chance_percent": 20,
            }
        },
    }


def test_ingest_preserves_forecast_and_metadata():
    store = NoaaForecastStore(clock=lambda: 100.0)
    result = store.ingest(event())
    assert result.area == "Macomb County"
    assert result.low_f == 42
    assert result.period == "tonight"
    assert result.frequency_hz == 162550000
    assert result.geographically_scoped
    assert store.latest() == result


def test_unscoped_forecast_is_not_assumed_local():
    result = NoaaForecastStore().ingest(event(area=None))
    assert result.area is None
    assert not result.geographically_scoped


def test_reception_age_does_not_claim_forecast_validity():
    now = [100.0]
    store = NoaaForecastStore(clock=lambda: now[0])
    store.ingest(event())
    now[0] = 115.0
    assert store.age_seconds() == 15.0


@pytest.mark.parametrize(
    "mutation",
    [
        lambda e: e.update(event="invalid"),
        lambda e: e.update(forecast_area=12),
        lambda e: e.update(forecast_revision=-1),
        lambda e: e["completed_forecast"]["forecast"].update(period=""),
        lambda e: e["completed_forecast"]["forecast"].update(high_f=float("nan")),
        lambda e: e["completed_forecast"]["forecast"].update(precipitation_chance_percent=120),
    ],
)
def test_invalid_events_do_not_replace_snapshot(mutation):
    store = NoaaForecastStore()
    original = store.ingest(event())
    broken = event()
    mutation(broken)
    with pytest.raises(ValueError):
        store.ingest(broken)
    assert store.latest() == original
