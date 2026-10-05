# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from datetime import datetime, timezone
import pytest
from controllers.weather import WeatherAlert, WeatherAlertCertainty, WeatherAlertSeverity, WeatherAlertUrgency, WeatherLocation
from services.weather.weather_alert_runtime import WeatherAlertRuntime

class _Subscriber:
    def subscribe(self, topic): self.topic = topic
    def receive(self): raise RuntimeError("unused")
    def close(self): pass
class _Provider:
    def __init__(self): self.alerts = ()
    def active_alerts(self, location): self.location = location; return self.alerts
class _Publisher:
    def __init__(self): self.alerts = []
    def publish(self, alert): self.alerts.append(alert)

def _alert(headline="Warning"):
    return WeatherAlert(identifier="alert-1", event="Severe Thunderstorm Warning", headline=headline, description="Storm", instruction=None, severity=WeatherAlertSeverity.SEVERE, urgency=WeatherAlertUrgency.IMMEDIATE, certainty=WeatherAlertCertainty.OBSERVED, effective_at=datetime(2026,9,18,17,0,tzinfo=timezone.utc), onset_at=None, expires_at=None, sender="NWS", source="nws")
def _runtime():
    provider=_Provider(); publisher=_Publisher()
    return WeatherAlertRuntime(provider,publisher,_Subscriber(),network_allowed=lambda: True),provider,publisher

def test_poll_publishes_new_alert_only_once():
    runtime,provider,publisher=_runtime(); provider.alerts=(_alert(),); location=WeatherLocation(42.8,-83.0,"test","test")
    assert runtime.poll_once(location)==1
    assert runtime.poll_once(location)==0
    assert len(publisher.alerts)==1
    assert publisher.alerts[0].alert==_alert()
    assert publisher.alerts[0].operation.value=="active"

def test_poll_republishes_changed_alert():
    runtime,provider,publisher=_runtime(); location=WeatherLocation(42.8,-83.0,"test","test")
    provider.alerts=(_alert("First"),); runtime.poll_once(location); provider.alerts=(_alert("Updated"),)
    assert runtime.poll_once(location)==1
    assert [event.alert.headline for event in publisher.alerts]==["First","Updated"]
    assert publisher.alerts[0].correlation_id==publisher.alerts[1].correlation_id

def test_alert_can_be_published_again_after_leaving_active_set():
    runtime,provider,publisher=_runtime(); location=WeatherLocation(42.8,-83.0,"test","test")
    provider.alerts=(_alert(),); runtime.poll_once(location); provider.alerts=(); runtime.poll_once(location); provider.alerts=(_alert(),)
    assert runtime.poll_once(location)==1
    assert len(publisher.alerts)==3
    assert publisher.alerts[1].operation.value=="cleared"
    assert publisher.alerts[2].operation.value=="active"
    assert publisher.alerts[0].correlation_id!=publisher.alerts[2].correlation_id

def test_rejects_polling_faster_than_nws_guidance():
    with pytest.raises(ValueError,match="at least 30 seconds"):
        WeatherAlertRuntime(_Provider(),_Publisher(),_Subscriber(),poll_interval_seconds=29.0)


def test_service_reads_persisted_mode_and_preserves_alerts_offline(tmp_path):
    from unittest.mock import Mock
    from controllers.connectivity.online_mode import OnlineModeController, saved_online_mode
    path = tmp_path / "online-mode.json"
    mode = OnlineModeController(path)
    provider = Mock()
    provider.active_alerts.return_value = (_alert(),)
    publisher = _Publisher()
    runtime = WeatherAlertRuntime(provider, publisher, _Subscriber(),
                                  network_allowed=lambda: saved_online_mode(path))
    location = WeatherLocation(42.8, -83.0, "test", "test")
    assert runtime.poll_once(location) == 1
    mode.set_online(False)
    provider.active_alerts.return_value = ()
    assert runtime.poll_once(location) == 0
    provider.active_alerts.assert_called_once_with(location)
    assert len(publisher.alerts) == 1
    mode.set_online(True)
    assert runtime.poll_once(location) == 1
    assert publisher.alerts[-1].operation.value == "cleared"
