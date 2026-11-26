# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Normalized calendar models without provider-specific identifiers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class CalendarCapabilities:
    can_read: bool = True
    can_create: bool = False
    can_update: bool = False
    can_delete: bool = False
    supports_incremental_sync: bool = False
    supports_invites: bool = False


@dataclass(frozen=True)
class CalendarEvent:
    account_id: str
    calendar_id: str
    event_id: str
    title: str
    starts_at: datetime
    ends_at: datetime
    all_day: bool = False
    location: str | None = None
    recurrence_id: str | None = None

    def __post_init__(self) -> None:
        if not self.account_id or not self.calendar_id or not self.event_id:
            raise ValueError("Calendar events require account, calendar, and event IDs")
        if self.starts_at.tzinfo is None or self.ends_at.tzinfo is None:
            raise ValueError("Calendar event timestamps must be timezone-aware")
        if self.ends_at <= self.starts_at:
            raise ValueError("Calendar event end must follow start")
