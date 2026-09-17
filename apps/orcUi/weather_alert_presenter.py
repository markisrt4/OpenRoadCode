# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Presentation mapping for weather-alert messages consumed by orcUi."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from messaging.contracts.weather import WeatherAlertData


@dataclass(frozen=True, slots=True)
class WeatherAlertPresentationState:
    """Toolkit-neutral weather-alert state ready for shell presentation."""

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


class WeatherAlertPresenter:
    """Map a public weather-alert message into shell presentation state."""

    @staticmethod
    def present(data: WeatherAlertData) -> WeatherAlertPresentationState:
        return WeatherAlertPresentationState(
            alert_id=data.alert_id,
            event=data.event,
            headline=data.headline,
            description=data.description,
            instruction=data.instruction,
            severity=data.severity,
            urgency=data.urgency,
            certainty=data.certainty,
            effective_at=datetime.fromisoformat(data.effective_at),
            onset_at=(
                None if data.onset_at is None else datetime.fromisoformat(data.onset_at)
            ),
            expires_at=(
                None if data.expires_at is None else datetime.fromisoformat(data.expires_at)
            ),
            sender=data.sender,
        )
