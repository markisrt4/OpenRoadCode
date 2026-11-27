# SPDX-License-Identifier: MIT
"""Aggregate cached events from enabled calendar accounts."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .calendar_accounts import load_accounts
from .calendar_event_cache import CalendarEventCache
from .calendar_models import CalendarCapabilities, CalendarEvent
from .calendar_provider_factory import CalendarAccountPaths
from .calendar_provider_if import CalendarProviderIf
from .calendar_selection import load_disabled_calendar_ids


class MultiAccountCachedProvider(CalendarProviderIf):
    """Read account-scoped snapshots through the existing provider contract."""

    def __init__(self, accounts_file: Path, metadata_root: Path, cache: CalendarEventCache) -> None:
        self._accounts_file = accounts_file
        self._metadata_root = metadata_root
        self._cache = cache

    @property
    def capabilities(self) -> CalendarCapabilities:
        return CalendarCapabilities(can_read=True)

    def list_events(self, start: datetime, end: datetime) -> list[CalendarEvent]:
        selections = {
            account.account_id: load_disabled_calendar_ids(
                CalendarAccountPaths(self._metadata_root, account).selection
            )
            for account in load_accounts(self._accounts_file)
            if account.enabled
        }
        return [
            event
            for event in self._cache.list_events(start, end)
            if event.account_id in selections
            and event.calendar_id not in selections[event.account_id]
        ]
