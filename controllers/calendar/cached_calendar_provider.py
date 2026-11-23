# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Provider adapter for offline calendar events."""

from __future__ import annotations

from datetime import datetime

from .calendar_event_cache import CalendarEventCache
from .calendar_models import CalendarCapabilities, CalendarEvent
from .calendar_provider_if import CalendarProviderIf


class CachedCalendarProvider(CalendarProviderIf):
    """Expose persisted events through the normal provider interface."""

    def __init__(self, account_id: str, cache: CalendarEventCache) -> None:
        if not account_id:
            raise ValueError("Account ID is required")
        self._account_id = account_id
        self._cache = cache

    @property
    def capabilities(self) -> CalendarCapabilities:
        return CalendarCapabilities(can_read=True)

    def list_events(self, start: datetime, end: datetime) -> list[CalendarEvent]:
        return [
            event for event in self._cache.list_events(start, end)
            if event.account_id == self._account_id
        ]
