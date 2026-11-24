# SPDX-License-Identifier: MIT
"""Toolkit-independent calendar agenda presentation."""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone, tzinfo

from .calendar_models import CalendarEvent
from .calendar_provider_if import CalendarProviderIf


@dataclass(frozen=True)
class AgendaDay:
    """Events visible on one local calendar date."""

    day: date
    events: tuple[CalendarEvent, ...]


class CalendarAgendaController:
    """Build a bounded agenda from an injected read-only calendar provider."""

    def __init__(self, provider: CalendarProviderIf, display_timezone: tzinfo) -> None:
        self._provider = provider
        self._timezone = display_timezone

    def load(self, first_day: date, days: int = 7) -> tuple[AgendaDay, ...]:
        """Return nonempty days, including ongoing and multi-day appointments.

        Call from a background worker when the provider performs disk I/O.
        All-day dates use the normalized UTC date representation.
        """
        if not 1 <= days <= 31:
            raise ValueError("Agenda window must contain 1 to 31 days")
        last_day = first_day + timedelta(days=days)
        start = datetime.combine(first_day, time.min, self._timezone)
        end = datetime.combine(last_day, time.min, self._timezone)
        utc_start = datetime.combine(first_day, time.min, timezone.utc)
        utc_end = datetime.combine(last_day, time.min, timezone.utc)
        events = self._provider.list_events(min(start, utc_start), max(end, utc_end))
        groups = []
        for offset in range(days):
            day = first_day + timedelta(days=offset)
            following = day + timedelta(days=1)
            lower = datetime.combine(day, time.min, self._timezone)
            upper = datetime.combine(following, time.min, self._timezone)
            visible = [
                event
                for event in events
                if (
                    event.starts_at.date() <= day < event.ends_at.date()
                    if event.all_day
                    else event.starts_at < upper and event.ends_at > lower
                )
            ]
            visible.sort(
                key=lambda event: (
                    not event.all_day,
                    event.starts_at.astimezone(timezone.utc),
                    event.title.casefold(),
                    event.calendar_id,
                    event.event_id,
                )
            )
            if visible:
                groups.append(AgendaDay(day, tuple(visible)))
        return tuple(groups)
