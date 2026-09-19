# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
from datetime import datetime,timedelta,timezone
from apps.orcUi.frontend.tk.weather_alert_banner import weather_alert_expiration_text
from ui.weather import WeatherAlertUiEvent

def _alert(expires_at):
    now=datetime(2026,9,19,1,0,tzinfo=timezone.utc)
    return WeatherAlertUiEvent("id","corr","active",None,"Warning","Headline","Description",None,"severe","immediate","observed",now,None,expires_at,"NWS")

def test_expiration_text_counts_down_minutes():
    now=datetime(2026,9,19,1,0,tzinfo=timezone.utc)
    assert weather_alert_expiration_text(_alert(now+timedelta(minutes=18)),now)=="Expires in 18 min"

def test_expiration_text_formats_hours():
    now=datetime(2026,9,19,1,0,tzinfo=timezone.utc)
    assert weather_alert_expiration_text(_alert(now+timedelta(minutes=90)),now)=="Expires in 1h 30m"

def test_expiration_text_marks_expired():
    now=datetime(2026,9,19,1,0,tzinfo=timezone.utc)
    assert weather_alert_expiration_text(_alert(now),now)=="EXPIRED"

def test_expiration_text_is_empty_without_expiration():
    now=datetime(2026,9,19,1,0,tzinfo=timezone.utc)
    assert weather_alert_expiration_text(_alert(None),now)==""
