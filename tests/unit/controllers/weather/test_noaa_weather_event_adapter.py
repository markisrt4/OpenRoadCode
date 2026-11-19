"""Hardware-free NOAA ZMQ event decoding tests."""

from __future__ import annotations

import json

import pytest

from controllers.weather.noaa_forecast_store import NoaaForecastStore
from controllers.weather.noaa_weather_event_adapter import (
    NoaaWeatherEventAdapter,
    decode_noaa_forecast_frame,
)


def valid_event():
    return {
        "event": "noaa_forecast_completed",
        "forecast_area": None,
        "forecast_areas": [],
        "forecast_revision": 1,
        "forecast_cycle": 0,
        "completed_forecast": {
            "forecast": {"period": "tonight", "conditions": "cloudy"}
        },
    }


def frame(event=None, *, topic=b"noaa.forecast", schema=1):
    envelope = {"schema_version": schema, "payload": valid_event() if event is None else event}
    return topic + b" " + json.dumps(envelope).encode()


def test_decodes_and_ingests_real_envelope_shape():
    store = NoaaForecastStore(clock=lambda: 50.0)
    adapter = NoaaWeatherEventAdapter(store)
    snapshot = adapter.ingest_frame(frame())
    assert snapshot.period == "tonight"
    assert snapshot.area is None
    assert store.latest() is snapshot


@pytest.mark.parametrize(
    "message",
    [
        b"",
        b"receiver {}",
        b"noaa.forecast not-json",
        b"noaa.forecast []",
        frame(schema=2),
        frame(event={"event": "other"}),
        b"noaa.forecast " + json.dumps({"schema_version": 1, "payload": []}).encode(),
    ],
)
def test_rejects_invalid_envelopes(message):
    with pytest.raises(ValueError):
        decode_noaa_forecast_frame(message)


def test_bad_frame_preserves_previous_forecast():
    store = NoaaForecastStore()
    adapter = NoaaWeatherEventAdapter(store)
    original = adapter.ingest_frame(frame())
    with pytest.raises(ValueError):
        adapter.ingest_frame(frame(schema=999))
    assert store.latest() is original
