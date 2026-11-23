# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Read-only CalDAV provider with per-calendar failure isolation."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from collections.abc import Collection
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

_LOG = logging.getLogger(__name__)


@dataclass(frozen=True)
class CalendarSyncStatus:
    calendar_id: str
    ok: bool
    disabled: bool = False
    resource_count: int = 0
    event_count: int = 0
    skipped_resources: int = 0
    error: str | None = None


class CalDavCalendarProvider(CalendarProviderIf):
    """Fetch calendars independently; report partial results without hiding failures."""

    def __init__(
        self,
        account_id: str,
        adapter: CalDavAdapter,
        disabled_calendar_ids: Collection[str] = (),
    ) -> None:
        if not account_id:
            raise ValueError("CalDAV account ID is required")
        self._account_id = account_id
        self._adapter = adapter
        self._disabled_calendar_ids = frozenset(disabled_calendar_ids)
        self.last_sync_status: list[CalendarSyncStatus] = []

    @property
    def capabilities(self) -> CalendarCapabilities:
        return CalendarCapabilities(can_read=True)

    def list_events(self, start: datetime, end: datetime) -> list[CalendarEvent]:
        if start.tzinfo is None or end.tzinfo is None or end <= start:
            raise ValueError("Expected timezone-aware, increasing time range")
        self.last_sync_status = []
        started = time.monotonic()
        _LOG.info("Calendar discovery started")
        calendars = self._adapter.discover_calendars()
        _LOG.info("Calendar discovery completed: %d calendars in %.1fs", len(calendars), time.monotonic() - started)
        events: list[CalendarEvent] = []
        for index, calendar in enumerate(calendars, 1):
            calendar_started = time.monotonic()
            _LOG.info("Calendar %d/%d: starting", index, len(calendars))
            if calendar.href in self._disabled_calendar_ids:
                self.last_sync_status.append(
                    CalendarSyncStatus(calendar.href, False, disabled=True)
                )
                _LOG.info("Calendar %d/%d: disabled", index, len(calendars))
                continue
            events.extend(self._read_calendar(calendar, start, end))
            status = self.last_sync_status[-1]
            _LOG.info(
                "Calendar %d/%d: %s resources=%d events=%d skipped=%d elapsed=%.1fs",
                index, len(calendars), "ok" if status.ok else status.error or "failed",
                status.resource_count, status.event_count, status.skipped_resources,
                time.monotonic() - calendar_started,
            )
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
        skipped_reasons: dict[str, int] = {}
        for resource in resources:
            try:
                parsed = parse_icalendar_events(resource.icalendar, self._account_id, calendar.href)
            except (ValueError, UnsupportedCalendarEventError) as error:
                skipped += 1
                reason = (
                    "unsupported_recurrence"
                    if isinstance(error, UnsupportedCalendarEventError)
                    else "invalid_calendar_data"
                )
                skipped_reasons[reason] = skipped_reasons.get(reason, 0) + 1
                continue
            events.extend(
                event for event in parsed if event.starts_at < end and event.ends_at > start
            )
        if skipped_reasons:
            _LOG.warning("Calendar resources skipped by reason: %s", skipped_reasons)
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
