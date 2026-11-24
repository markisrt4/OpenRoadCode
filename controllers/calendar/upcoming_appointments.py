# SPDX-License-Identifier: MIT
"""Provider-independent upcoming appointment selection."""

from datetime import datetime, timezone

from .calendar_agenda import CalendarAgendaController
from .calendar_models import CalendarEvent


def upcoming_appointments(
    controller: CalendarAgendaController, now: datetime, *, limit: int = 3
) -> tuple[CalendarEvent, ...]:
    """Return the next timed appointments within seven local calendar days."""
    if now.utcoffset() is None:
        raise ValueError("Current time must be timezone-aware")
    if limit < 1:
        raise ValueError("Limit must be positive")
    unique = {}
    for group in controller.load(now.date(), 7):
        for event in group.events:
            if not event.all_day and event.starts_at.astimezone(timezone.utc) >= now.astimezone(
                timezone.utc
            ):
                key = (event.account_id, event.calendar_id, event.event_id, event.recurrence_id)
                unique[key] = event
    return tuple(
        sorted(unique.values(), key=lambda event: event.starts_at.astimezone(timezone.utc))
    )[:limit]
