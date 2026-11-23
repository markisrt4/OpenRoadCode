# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Synchronize CalDAV into the offline cache without deleting failed calendars."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .caldav_provider import CalDavCalendarProvider, CalendarSyncStatus
from .calendar_event_cache import CalendarEventCache


@dataclass(frozen=True)
class CalendarSyncResult:
    statuses: tuple[CalendarSyncStatus, ...]
    cached_calendars: int


class CalendarSyncWorker:
    """One sync pass; callers may schedule it off the UI thread."""

    def __init__(
        self, account_id: str, provider: CalDavCalendarProvider,
        cache: CalendarEventCache,
    ) -> None:
        self._account_id = account_id
        self._provider = provider
        self._cache = cache

    def sync_once(self, start: datetime, end: datetime) -> CalendarSyncResult:
        events = self._provider.list_events(start, end)
        statuses = tuple(self._provider.last_sync_status)
        saved = 0
        for status in statuses:
            if not status.ok or status.disabled:
                continue
            calendar_events = [
                event for event in events
                if event.account_id == self._account_id
                and event.calendar_id == status.calendar_id
            ]
            self._cache.replace_calendar_window(
                self._account_id, status.calendar_id, start, end, calendar_events
            )
            saved += 1
        return CalendarSyncResult(statuses=statuses, cached_calendars=saved)
