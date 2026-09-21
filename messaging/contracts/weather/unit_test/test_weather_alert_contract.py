# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
from datetime import datetime,timezone
from unittest.mock import Mock
import pytest
from controllers.weather import WeatherAlert,WeatherAlertCertainty,WeatherAlertEvent,WeatherAlertOperation,WeatherAlertSeverity,WeatherAlertUrgency
from messaging.contracts.weather import WEATHER_ALERT_TOPIC,WeatherAlertPublisher,decode_weather_alert,encode_weather_alert,validate_weather_alert

def _alert():
    return WeatherAlert(identifier="urn:nws:alert:test-123",event="Severe Thunderstorm Warning",headline="Warning issued",description="Storms.",instruction="Move indoors.",severity=WeatherAlertSeverity.SEVERE,urgency=WeatherAlertUrgency.IMMEDIATE,certainty=WeatherAlertCertainty.OBSERVED,effective_at=datetime(2026,9,17,18,tzinfo=timezone.utc),onset_at=None,expires_at=datetime(2026,9,17,19,tzinfo=timezone.utc),sender="NWS",source="nws")
def _event():return WeatherAlertEvent(_alert(),"corr-1",WeatherAlertOperation.ACTIVE)

def test_encode_preserves_lifecycle_fields():
    p=encode_weather_alert(_event())
    assert p["version"]==1 and p["source"]=="nws"
    assert p["data"]["identifier"]=="urn:nws:alert:test-123"
    assert p["data"]["correlation_id"]=="corr-1"
    assert p["data"]["operation"]=="active" and p["data"]["clear_reason"] is None
def test_decode_returns_typed_message():
    m=decode_weather_alert(encode_weather_alert(_event()))
    assert m.data.identifier=="urn:nws:alert:test-123" and m.data.correlation_id=="corr-1"
def test_nullable_fields_are_supported():
    a=_alert()
    a=WeatherAlert(a.identifier,a.event,a.headline,a.description,None,a.severity,a.urgency,a.certainty,a.effective_at,None,None,a.sender,a.source)
    p=encode_weather_alert(WeatherAlertEvent(a,"corr-1",WeatherAlertOperation.ACTIVE))
    assert p["data"]["instruction"] is None and p["data"]["onset_at"] is None and p["data"]["expires_at"] is None
def test_validator_rejects_unknown_severity():
    p=encode_weather_alert(_event());p["data"]["severity"]="catastrophically-inconvenient"
    with pytest.raises(ValueError):validate_weather_alert(p)
def test_validator_rejects_naive_timestamp():
    p=encode_weather_alert(_event());p["data"]["effective_at"]="2026-09-17T18:00:00"
    with pytest.raises(ValueError):validate_weather_alert(p)
def test_publisher_uses_weather_alert_topic():
    transport=Mock();WeatherAlertPublisher(transport).publish(_event())
    topic,payload=transport.publish.call_args.args
    assert topic==WEATHER_ALERT_TOPIC and payload["data"]["identifier"]=="urn:nws:alert:test-123"
