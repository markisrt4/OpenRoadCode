# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from controllers.weather.providers.nws_weather_alert_provider import NwsWeatherAlertProvider
from controllers.weather.weather_alert import (
    WeatherAlertCertainty,
    WeatherAlertSeverity,
    WeatherAlertUrgency,
)
from controllers.weather.weather_state import WeatherLocation


class _Response:
    def __init__(self, payload):
        self._payload = payload
    def raise_for_status(self):
        pass
    def json(self):
        return self._payload


class _Session:
    def __init__(self, payload):
        self.payload = payload
        self.request = None
    def get(self, url, **kwargs):
        self.request = (url, kwargs)
        return _Response(self.payload)


def test_normalizes_active_nws_alert():
    session = _Session({"features": [{
        "id": "https://api.weather.gov/alerts/test",
        "properties": {
            "event": "Severe Thunderstorm Warning",
            "headline": "Severe Thunderstorm Warning issued September 18",
            "description": "A severe thunderstorm was located nearby.",
            "instruction": "Move indoors.",
            "severity": "Severe",
            "urgency": "Immediate",
            "certainty": "Observed",
            "effective": "2026-09-18T13:00:00-04:00",
            "onset": "2026-09-18T13:00:00-04:00",
            "expires": "2026-09-18T14:00:00-04:00",
            "senderName": "NWS Detroit/Pontiac MI",
        },
    }]})
    provider = NwsWeatherAlertProvider(session=session)
    alerts = provider.active_alerts(WeatherLocation(42.8028, -83.0127, "Romeo", "test"))

    assert len(alerts) == 1
    alert = alerts[0]
    assert alert.alert_id == "https://api.weather.gov/alerts/test"
    assert alert.event == "Severe Thunderstorm Warning"
    assert alert.severity is WeatherAlertSeverity.SEVERE
    assert alert.urgency is WeatherAlertUrgency.IMMEDIATE
    assert alert.certainty is WeatherAlertCertainty.OBSERVED
    assert alert.source == "nws"
    assert alert.effective_at.tzinfo is not None
    url, request = session.request
    assert url == provider.URL
    assert request["params"]["point"] == "42.8028,-83.0127"
    assert request["headers"]["Accept"] == "application/geo+json"
    assert "openroadcode.org" in request["headers"]["User-Agent"]


def test_unknown_cap_values_normalize_to_unknown():
    alert = NwsWeatherAlertProvider._alert({
        "id": "alert-1",
        "properties": {
            "event": "Test",
            "severity": "Undefined",
            "urgency": "Undefined",
            "certainty": "Undefined",
            "effective": "2026-09-18T13:00:00Z",
        },
    })
    assert alert.severity is WeatherAlertSeverity.UNKNOWN
    assert alert.urgency is WeatherAlertUrgency.UNKNOWN
    assert alert.certainty is WeatherAlertCertainty.UNKNOWN
