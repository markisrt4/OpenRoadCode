# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Read-only CalDAV provider with per-calendar failure isolation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .caldav_adapter import (
    CalDavAdapter,
    CalDavAuthenticationError,
    CalDavCalendar,
    CalDavHttpError,
    CalDavTimeoutError,
)
from .calendar_models import CalendarCapabilities, CalendarEvent
from .calendar_provider_if import CalendarProviderIf
from .icalendar_parser import UnsupportedCalendarEventError, parse_icalendar_events


@dataclass(frozen=True)
class CalendarSyncStatus:
    calendar_id: str
    ok: bool
    resource_count: int = 0
    event_count: int = 0
    skipped_resources: int = 0
    error: str | None = None


class CalDavCalendarProvider(CalendarProviderIf):
    """Fetch calendars independently; report partial results without hiding failures."""

    def __init__(self, account_id: str, adapter: CalDavAdapter) -> None:
        if not account_id:
            raise ValueError("CalDAV account ID is required")
        self._account_id = account_id
        self._adapter = adapter
        self.last_sync_status: list[CalendarSyncStatus] = []

    @property
    def capabilities(self) -> CalendarCapabilities:
        return CalendarCapabilities(can_read=True)

    def list_events(self, start: datetime, end: datetime) -> list[CalendarEvent]:
        if start.tzinfo is None or end.tzinfo is None or end <= start:
            raise ValueError("Expected timezone-aware, increasing time range")
        self.last_sync_status = []
        calendars = self._adapter.discover_calendars()
        events: list[CalendarEvent] = []
        for calendar in calendars:
            events.extend(self._read_calendar(calendar, start, end))
        return sorted(events, key=lambda event: (event.starts_at, event.event_id))

    def _read_calendar(
        self, calendar: CalDavCalendar, start: datetime, end: datetime
    ) -> list[CalendarEvent]:
        try:
            resources = self._adapter.query_event_resources(calendar, start, end)
        except (CalDavTimeoutError, CalDavHttpError, CalDavAuthenticationError) as error:
            self.last_sync_status.append(
                CalendarSyncStatus(calendar.href, False, error=type(error).__name__)
            )
            return []
        events: list[CalendarEvent] = []
        skipped = 0
        for resource in resources:
            try:
                parsed = parse_icalendar_events(
                    resource.icalendar, self._account_id, calendar.href
                )
            except (ValueError, UnsupportedCalendarEventError):
                skipped += 1
                continue
            events.extend(
                event
                for event in parsed
                if event.starts_at < end and event.ends_at > start
            )
        self.last_sync_status.append(
            CalendarSyncStatus(
                calendar.href,
                True,
                resource_count=len(resources),
                event_count=len(events),
                skipped_resources=skipped,
            )
        )
        return events
