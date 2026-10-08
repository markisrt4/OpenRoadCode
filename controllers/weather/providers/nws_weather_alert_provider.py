# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""National Weather Service active-alert provider."""
from __future__ import annotations
from datetime import datetime
import requests
from controllers.weather.weather_alert import WeatherAlert, WeatherAlertCertainty, WeatherAlertSeverity, WeatherAlertUrgency
from controllers.weather.weather_state import WeatherLocation

class NwsWeatherAlertProvider:
    URL="https://api.weather.gov/alerts/active"; USER_AGENT="(openroadcode.org, OpenRoadCode)"
    def __init__(self,*,timeout_seconds:float=10.0,session:requests.Session|None=None,user_agent:str=USER_AGENT)->None:
        self._timeout_seconds=timeout_seconds; self._session=session or requests.Session(); self._user_agent=user_agent
    @property
    def provider_id(self)->str: return "nws"
    def active_alerts(self,location:WeatherLocation)->tuple[WeatherAlert,...]:
        response=self._session.get(self.URL,params={"point":f"{location.latitude},{location.longitude}"},headers={"User-Agent":self._user_agent,"Accept":"application/geo+json"},timeout=self._timeout_seconds)
        response.raise_for_status(); payload=response.json(); features=payload.get("features") if isinstance(payload,dict) else None
        if not isinstance(features,list): raise ValueError("NWS returned incomplete alert data")
        return tuple(self._alert(feature) for feature in features)
    @classmethod
    def _alert(cls,feature:dict)->WeatherAlert:
        p=feature.get("properties")
        if not isinstance(p,dict): raise ValueError("NWS alert is missing properties")
        identifier=feature.get("id") or p.get("id")
        if not isinstance(identifier,str) or not identifier: raise ValueError("NWS alert is missing an id")
        return WeatherAlert(identifier=identifier,event=cls._text(p.get("event"),"Weather Alert"),headline=cls._text(p.get("headline"),cls._text(p.get("event"),"Weather Alert")),description=cls._text(p.get("description"),""),instruction=cls._optional_text(p.get("instruction")),severity=cls._enum(WeatherAlertSeverity,p.get("severity")),urgency=cls._enum(WeatherAlertUrgency,p.get("urgency")),certainty=cls._enum(WeatherAlertCertainty,p.get("certainty")),effective_at=cls._datetime(p.get("effective"),"effective"),onset_at=cls._optional_datetime(p.get("onset")),expires_at=cls._optional_datetime(p.get("expires")),sender=cls._text(p.get("senderName") or p.get("sender"),"National Weather Service"),source="nws")
    @staticmethod
    def _enum(t,v):
        try:return t(str(v).lower())
        except ValueError:return t.UNKNOWN
    @staticmethod
    def _text(v,f): return v.strip() if isinstance(v,str) and v.strip() else f
    @classmethod
    def _optional_text(cls,v):
        x=cls._text(v,""); return x or None
    @staticmethod
    def _datetime(v,field):
        if not isinstance(v,str) or not v: raise ValueError(f"NWS alert is missing {field}")
        x=datetime.fromisoformat(v.replace("Z","+00:00"))
        if x.tzinfo is None: raise ValueError(f"NWS alert {field} must include a timezone")
        return x
    @classmethod
    def _optional_datetime(cls,v): return None if v is None else cls._datetime(v,"timestamp")
