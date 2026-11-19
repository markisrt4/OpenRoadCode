# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Decode SDRForge NOAA forecast frames without depending on SDR hardware."""

from __future__ import annotations

import json
from collections.abc import Mapping

from controllers.weather.noaa_forecast_store import NoaaForecastSnapshot, NoaaForecastStore

NOAA_FORECAST_TOPIC = b"noaa.forecast"


def decode_noaa_forecast_frame(frame: bytes) -> Mapping[str, object]:
    """Validate a versioned single-frame SDRForge ZMQ telemetry message."""
    if not isinstance(frame, bytes):
        raise ValueError("NOAA frame must be bytes")
    topic, separator, body = frame.partition(b" ")
    if not separator or topic != NOAA_FORECAST_TOPIC:
        raise ValueError("unexpected NOAA forecast topic")
    try:
        envelope = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid NOAA forecast JSON") from exc
    if not isinstance(envelope, dict) or envelope.get("schema_version") != 1:
        raise ValueError("unsupported NOAA forecast schema")
    payload = envelope.get("payload")
    if not isinstance(payload, dict) or payload.get("event") != "noaa_forecast_completed":
        raise ValueError("invalid NOAA forecast payload")
    return payload


class NoaaWeatherEventAdapter:
    """Convert transport frames into validated store snapshots."""

    def __init__(self, store: NoaaForecastStore) -> None:
        self._store = store

    def ingest_frame(self, frame: bytes) -> NoaaForecastSnapshot:
        """Decode a frame and update the forecast store atomically."""
        return self._store.ingest(decode_noaa_forecast_frame(frame))
