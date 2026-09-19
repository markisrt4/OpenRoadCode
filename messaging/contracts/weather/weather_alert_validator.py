# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
from collections.abc import Mapping
from datetime import datetime
from typing import Any
from controllers.weather import WeatherAlertCertainty,WeatherAlertSeverity,WeatherAlertUrgency,WeatherAlertOperation,WeatherAlertClearReason
SCHEMA_VERSION=1
def validate_weather_alert(p:Mapping[str,Any])->None:
    if p.get("version")!=SCHEMA_VERSION:raise ValueError("unsupported weather alert schema version")
    if not isinstance(p.get("source"),str) or not p["source"]:raise ValueError("source must be a non-empty string")
    d=p.get("data")
    if not isinstance(d,Mapping):raise ValueError("data must be an object")
    req={"identifier","correlation_id","operation","clear_reason","event","headline","description","instruction","severity","urgency","certainty","effective_at","onset_at","expires_at","sender"}
    if set(d)!=req:raise ValueError("weather alert data fields do not match schema")
    for n in ("identifier","correlation_id","event","headline","description","sender"):
        if not isinstance(d[n],str) or not d[n]:raise ValueError(f"{n} must be a non-empty string")
    _enum(d["operation"],WeatherAlertOperation,"operation"); _enum(d["severity"],WeatherAlertSeverity,"severity"); _enum(d["urgency"],WeatherAlertUrgency,"urgency"); _enum(d["certainty"],WeatherAlertCertainty,"certainty")
    if d["operation"]=="active" and d["clear_reason"] is not None:raise ValueError("active alert must not have clear_reason")
    if d["operation"]=="cleared":
        _enum(d["clear_reason"],WeatherAlertClearReason,"clear_reason")
    if d["instruction"] is not None and not isinstance(d["instruction"],str):raise ValueError("instruction must be null or a string")
    for n,null in (("effective_at",False),("onset_at",True),("expires_at",True)):_ts(d[n],n,null)
def _enum(v,t,n):
    if not isinstance(v,str):raise ValueError(f"{n} must be a string")
    try:t(v)
    except ValueError as e:raise ValueError(f"unsupported weather alert {n}: {v}") from e
def _ts(v,n,null):
    if v is None and null:return
    if not isinstance(v,str) or not v:raise ValueError(f"{n} must be an ISO-8601 timestamp")
    try:x=datetime.fromisoformat(v)
    except ValueError as e:raise ValueError(f"{n} must be an ISO-8601 timestamp") from e
    if x.tzinfo is None or x.utcoffset() is None:raise ValueError(f"{n} must include a timezone offset")
