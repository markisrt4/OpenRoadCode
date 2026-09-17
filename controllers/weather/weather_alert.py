# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Provider-neutral weather alert domain model."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class WeatherAlertSeverity(StrEnum):
    """CAP-compatible severity of a weather alert."""

    EXTREME = "extreme"
    SEVERE = "severe"
    MODERATE = "moderate"
    MINOR = "minor"
    UNKNOWN = "unknown"


class WeatherAlertUrgency(StrEnum):
    """CAP-compatible urgency of a weather alert."""

    IMMEDIATE = "immediate"
    EXPECTED = "expected"
    FUTURE = "future"
    PAST = "past"
    UNKNOWN = "unknown"


class WeatherAlertCertainty(StrEnum):
    """CAP-compatible certainty of a weather alert."""

    OBSERVED = "observed"
    LIKELY = "likely"
    POSSIBLE = "possible"
    UNLIKELY = "unlikely"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class WeatherAlert:
    """Normalized alert independent of the upstream weather provider."""

    alert_id: str
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
