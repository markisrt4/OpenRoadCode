# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Presentation mapping for weather-alert messages consumed by orcUi."""

from __future__ import annotations

from datetime import datetime

from messaging.contracts.weather import WeatherAlertData
from ui.weather import WeatherAlertUiEvent

# Backward-compatible local name while ingress callers migrate to the UI contract.
WeatherAlertPresentationState = WeatherAlertUiEvent


class WeatherAlertPresenter:
    """Map a public weather-alert message into a driver-facing UI event."""

    @staticmethod
    def present(data: WeatherAlertData) -> WeatherAlertUiEvent:
        return WeatherAlertUiEvent(
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
