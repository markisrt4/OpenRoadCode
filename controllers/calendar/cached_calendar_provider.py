# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Provider adapter for offline calendar events."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .calendar_event_cache import CalendarEventCache
from .calendar_models import CalendarCapabilities, CalendarEvent
from .calendar_provider_if import CalendarProviderIf
from .calendar_selection import load_disabled_calendar_ids


class CachedCalendarProvider(CalendarProviderIf):
    """Expose persisted events through the normal provider interface."""

    def __init__(
        self, account_id: str, cache: CalendarEventCache, selection_file: Path | None = None
    ) -> None:
        if not account_id:
            raise ValueError("Account ID is required")
        self._account_id = account_id
        self._cache = cache
        self._selection_file = selection_file

    @property
    def capabilities(self) -> CalendarCapabilities:
        return CalendarCapabilities(can_read=True)

    def list_events(self, start: datetime, end: datetime) -> list[CalendarEvent]:
        disabled = (
            load_disabled_calendar_ids(self._selection_file)
            if self._selection_file is not None
            else frozenset()
        )
        return [
            event
            for event in self._cache.list_events(start, end)
            if event.account_id == self._account_id and event.calendar_id not in disabled
        ]
