# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Provider-neutral weather alert domain model."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

class WeatherAlertSeverity(StrEnum):
    EXTREME="extreme"; SEVERE="severe"; MODERATE="moderate"; MINOR="minor"; UNKNOWN="unknown"
class WeatherAlertUrgency(StrEnum):
    IMMEDIATE="immediate"; EXPECTED="expected"; FUTURE="future"; PAST="past"; UNKNOWN="unknown"
class WeatherAlertCertainty(StrEnum):
    OBSERVED="observed"; LIKELY="likely"; POSSIBLE="possible"; UNLIKELY="unlikely"; UNKNOWN="unknown"
class WeatherAlertOperation(StrEnum):
    ACTIVE="active"; CLEARED="cleared"
class WeatherAlertClearReason(StrEnum):
    EXPIRED="expired"; CANCELLED="cancelled"; WITHDRAWN="withdrawn"

@dataclass(frozen=True, slots=True)
class WeatherAlert:
    """Normalized provider alert with opaque provider identity."""
    identifier: str
    event: str
    headline: str
    description: str
    instruction: str | None
    severity: WeatherAlertSeverity
    urgency: WeatherAlertUrgency
    certainty: WeatherAlertCertainty
    effective_at: datetime
    onset_at: datetime | None
    expires_at: datetime | None
    sender: str
    source: str

@dataclass(frozen=True, slots=True)
class WeatherAlertEvent:
    """One ORC lifecycle event for a normalized provider alert."""
    alert: WeatherAlert
    correlation_id: str
    operation: WeatherAlertOperation
    clear_reason: WeatherAlertClearReason | None = None
