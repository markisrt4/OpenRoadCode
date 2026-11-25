# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Combine calendar providers without coupling the UI to their protocols."""

from __future__ import annotations

from datetime import datetime

from .calendar_models import CalendarEvent
from .calendar_provider_if import CalendarProviderIf


class CalendarController:
    def __init__(self, providers: dict[str, CalendarProviderIf]) -> None:
        self._providers = dict(providers)

    def list_events(self, start: datetime, end: datetime) -> list[CalendarEvent]:
        if start.tzinfo is None or end.tzinfo is None or end <= start:
            raise ValueError("Query requires aware timestamps and a positive interval")
        events: list[CalendarEvent] = []
        for account_id, provider in self._providers.items():
            if not provider.capabilities.can_read:
                continue
            for event in provider.list_events(start, end):
                if event.account_id != account_id:
                    raise ValueError("Provider returned an event for another account")
                if event.starts_at < end and event.ends_at > start:
                    events.append(event)
        return sorted(
            events,
            key=lambda event: (
                event.starts_at,
                event.ends_at,
                event.account_id,
                event.calendar_id,
                event.event_id,
                event.recurrence_id or "",
            ),
        )
