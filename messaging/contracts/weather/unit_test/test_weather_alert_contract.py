# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from datetime import datetime, timezone
from unittest.mock import Mock

import pytest

from controllers.weather import (
    WeatherAlert,
    WeatherAlertCertainty,
    WeatherAlertSeverity,
    WeatherAlertUrgency,
)
from messaging.contracts.weather import (
    WEATHER_ALERT_TOPIC,
    WeatherAlertPublisher,
    decode_weather_alert,
    encode_weather_alert,
    validate_weather_alert,
)


def _alert() -> WeatherAlert:
    return WeatherAlert(
        alert_id="urn:nws:alert:test-123",
        event="Severe Thunderstorm Warning",
        headline="Severe Thunderstorm Warning issued for test area",
        description="Severe thunderstorms are occurring in the warned area.",
        instruction="Move indoors and stay away from windows.",
        severity=WeatherAlertSeverity.SEVERE,
        urgency=WeatherAlertUrgency.IMMEDIATE,
        certainty=WeatherAlertCertainty.OBSERVED,
        effective_at=datetime(2026, 9, 17, 18, 0, tzinfo=timezone.utc),
        onset_at=datetime(2026, 9, 17, 18, 0, tzinfo=timezone.utc),
        expires_at=datetime(2026, 9, 17, 19, 0, tzinfo=timezone.utc),
        sender="NWS Detroit/Pontiac MI",
        source="nws",
    )


def test_encode_preserves_normalized_alert_fields() -> None:
    payload = encode_weather_alert(_alert())

    assert payload["version"] == 1
    assert payload["source"] == "nws"
    assert payload["data"]["event"] == "Severe Thunderstorm Warning"
    assert payload["data"]["severity"] == "severe"
    assert payload["data"]["urgency"] == "immediate"
    assert payload["data"]["certainty"] == "observed"
    assert payload["data"]["effective_at"] == "2026-09-17T18:00:00+00:00"


def test_decode_returns_typed_message() -> None:
    message = decode_weather_alert(encode_weather_alert(_alert()))

    assert message.source == "nws"
    assert message.data.alert_id == "urn:nws:alert:test-123"
    assert message.data.instruction == "Move indoors and stay away from windows."
    assert message.data.expires_at == "2026-09-17T19:00:00+00:00"


def test_nullable_instruction_onset_and_expiration_are_supported() -> None:
    alert = _alert()
    alert = WeatherAlert(
        alert_id=alert.alert_id,
        event=alert.event,
        headline=alert.headline,
        description=alert.description,
        instruction=None,
        severity=alert.severity,
        urgency=alert.urgency,
        certainty=alert.certainty,
        effective_at=alert.effective_at,
        onset_at=None,
        expires_at=None,
        sender=alert.sender,
        source=alert.source,
    )

    payload = encode_weather_alert(alert)

    assert payload["data"]["instruction"] is None
    assert payload["data"]["onset_at"] is None
    assert payload["data"]["expires_at"] is None


def test_validator_rejects_unknown_severity() -> None:
    payload = encode_weather_alert(_alert())
    payload["data"]["severity"] = "catastrophically-inconvenient"

    with pytest.raises(ValueError):
        validate_weather_alert(payload)


def test_validator_rejects_naive_timestamp() -> None:
    payload = encode_weather_alert(_alert())
    payload["data"]["effective_at"] = "2026-09-17T18:00:00"

    with pytest.raises(ValueError):
        validate_weather_alert(payload)


def test_publisher_uses_weather_alert_topic() -> None:
    transport = Mock()
    publisher = WeatherAlertPublisher(transport)

    publisher.publish(_alert())

    topic, payload = transport.publish.call_args.args
    assert topic == WEATHER_ALERT_TOPIC
    assert payload["data"]["alert_id"] == "urn:nws:alert:test-123"
