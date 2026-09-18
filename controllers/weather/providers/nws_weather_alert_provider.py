# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""National Weather Service active-alert provider."""

from __future__ import annotations

from datetime import datetime
import requests

from controllers.weather.weather_alert import (
    WeatherAlert,
    WeatherAlertCertainty,
    WeatherAlertSeverity,
    WeatherAlertUrgency,
)
from controllers.weather.weather_state import WeatherLocation


class NwsWeatherAlertProvider:
    """Fetch and normalize active NWS alerts for a geographic point."""

    URL = "https://api.weather.gov/alerts/active"
    USER_AGENT = "(openroadcode.org, OpenRoadCode)"

    def __init__(
        self,
        *,
        timeout_seconds: float = 10.0,
        session: requests.Session | None = None,
        user_agent: str = USER_AGENT,
    ) -> None:
        self._timeout_seconds = timeout_seconds
        self._session = session or requests.Session()
        self._user_agent = user_agent

    @property
    def provider_id(self) -> str:
        return "nws"

    def active_alerts(self, location: WeatherLocation) -> tuple[WeatherAlert, ...]:
        response = self._session.get(
            self.URL,
            params={"point": f"{location.latitude},{location.longitude}"},
            headers={
                "User-Agent": self._user_agent,
                "Accept": "application/geo+json",
            },
            timeout=self._timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        features = payload.get("features") if isinstance(payload, dict) else None
        if not isinstance(features, list):
            raise ValueError("NWS returned incomplete alert data")
        return tuple(self._alert(feature) for feature in features)

    @classmethod
    def _alert(cls, feature: dict) -> WeatherAlert:
        properties = feature.get("properties")
        if not isinstance(properties, dict):
            raise ValueError("NWS alert is missing properties")
        alert_id = feature.get("id") or properties.get("id")
        if not isinstance(alert_id, str) or not alert_id:
            raise ValueError("NWS alert is missing an id")
        return WeatherAlert(
            alert_id=alert_id,
            event=cls._text(properties.get("event"), "Weather Alert"),
            headline=cls._text(properties.get("headline"), cls._text(properties.get("event"), "Weather Alert")),
            description=cls._text(properties.get("description"), ""),
            instruction=cls._optional_text(properties.get("instruction")),
            severity=cls._enum(WeatherAlertSeverity, properties.get("severity")),
            urgency=cls._enum(WeatherAlertUrgency, properties.get("urgency")),
            certainty=cls._enum(WeatherAlertCertainty, properties.get("certainty")),
            effective_at=cls._datetime(properties.get("effective"), "effective"),
            onset_at=cls._optional_datetime(properties.get("onset")),
            expires_at=cls._optional_datetime(properties.get("expires")),
            sender=cls._text(properties.get("senderName") or properties.get("sender"), "National Weather Service"),
            source="nws",
        )

    @staticmethod
    def _enum(enum_type, value):
        try:
            return enum_type(str(value).lower())
        except ValueError:
            return enum_type.UNKNOWN

    @staticmethod
    def _text(value, fallback: str) -> str:
        return value.strip() if isinstance(value, str) and value.strip() else fallback

    @classmethod
    def _optional_text(cls, value) -> str | None:
        text = cls._text(value, "")
        return text or None

    @staticmethod
    def _datetime(value, field: str) -> datetime:
        if not isinstance(value, str) or not value:
            raise ValueError(f"NWS alert is missing {field}")
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError(f"NWS alert {field} must include a timezone")
        return parsed

    @classmethod
    def _optional_datetime(cls, value) -> datetime | None:
        return None if value is None else cls._datetime(value, "timestamp")
