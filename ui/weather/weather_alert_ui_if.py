# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""! @brief Toolkit-independent event contract for weather alerts."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class WeatherAlertUiEvent:
    """One driver-facing weather alert event."""

    alert_id: str
    event: str
    headline: str
    description: str
    instruction: str | None
    severity: str
    urgency: str
    certainty: str
    effective_at: datetime
    onset_at: datetime | None
    expires_at: datetime | None
    sender: str


class WeatherAlertUiIf(ABC):
    """! @brief Receive asynchronous weather-alert events."""

    @abstractmethod
    def present_weather_alert(self, alert: WeatherAlertUiEvent) -> None:
        """! @brief Present one newly received or updated weather alert."""
        ...
