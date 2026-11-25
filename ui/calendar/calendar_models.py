# SPDX-License-Identifier: MIT
"""Immutable calendar data exposed to presentation consumers."""

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class CalendarEventView:
    """Displayable appointment without a provider dependency."""

    account_id: str
    calendar_id: str
    event_id: str
    title: str
    starts_at: datetime
    ends_at: datetime
    all_day: bool = False
    location: str | None = None
    recurrence_id: str | None = None


@dataclass(frozen=True)
class AgendaDayView:
    """Appointments grouped by local date."""

    day: date
    events: tuple[CalendarEventView, ...]


@dataclass(frozen=True)
class CalendarHealthView:
    """Synchronization status and data freshness."""

    status: str = "unavailable"
    stale: bool = False
    last_data_refresh_age_seconds: float | None = None


@dataclass(frozen=True)
class AgendaSnapshot:
    """Completed agenda read."""

    groups: tuple[AgendaDayView, ...]
    health: CalendarHealthView


@dataclass(frozen=True)
class AppointmentSnapshot:
    """Completed upcoming appointment read."""

    events: tuple[CalendarEventView, ...]
    health: CalendarHealthView


@dataclass(frozen=True)
class CalendarSelectionView:
    """One selectable calendar."""

    calendar_id: str
    name: str
    enabled: bool
