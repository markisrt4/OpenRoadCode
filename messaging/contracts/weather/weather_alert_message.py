# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Typed public weather alert message."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class WeatherAlertData:
    alert_id: str
    event: str
    headline: str
    description: str
    instruction: str | None
    severity: str
    urgency: str
    certainty: str
    effective_at: str
    onset_at: str | None
    expires_at: str | None
    sender: str


@dataclass(frozen=True, slots=True)
class WeatherAlertMessage:
    version: int
    source: str
    data: WeatherAlertData
