# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
from collections.abc import Mapping
from typing import Any
from controllers.weather import WeatherAlertEvent
from .weather_alert_message import WeatherAlertData,WeatherAlertMessage
from .weather_alert_validator import SCHEMA_VERSION,validate_weather_alert
def encode_weather_alert(event:WeatherAlertEvent)->dict[str,Any]:
    a=event.alert
    p={"version":SCHEMA_VERSION,"source":a.source,"data":{"identifier":a.identifier,"correlation_id":event.correlation_id,"operation":event.operation.value,"clear_reason":None if event.clear_reason is None else event.clear_reason.value,"event":a.event,"headline":a.headline,"description":a.description,"instruction":a.instruction,"severity":a.severity.value,"urgency":a.urgency.value,"certainty":a.certainty.value,"effective_at":a.effective_at.isoformat(),"onset_at":None if a.onset_at is None else a.onset_at.isoformat(),"expires_at":None if a.expires_at is None else a.expires_at.isoformat(),"sender":a.sender}}
    validate_weather_alert(p); return p
def decode_weather_alert(payload:Mapping[str,Any])->WeatherAlertMessage:
    validate_weather_alert(payload); d=payload["data"]
    return WeatherAlertMessage(version=payload["version"],source=payload["source"],data=WeatherAlertData(**{n:d[n] for n in WeatherAlertData.__dataclass_fields__}))
