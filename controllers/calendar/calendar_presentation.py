# SPDX-License-Identifier: MIT
"""Calendar presentation adapters without toolkit dependencies."""

from concurrent.futures import Future
from datetime import date
from pathlib import Path
from threading import Thread
from typing import Callable

from ui.calendar.calendar_models import (
    AgendaDayView,
    AgendaSnapshot,
    CalendarEventView,
    CalendarHealthView,
    CalendarSelectionView,
)
from ui.calendar.calendar_presentation_if import CalendarAgendaIf, CalendarSelectionIf

from .calendar_health import sample_calendar_health
from .calendar_models import CalendarEvent
from .calendar_query_if import CalendarQueryIf
from .calendar_selection import (
    load_calendar_catalog,
    load_disabled_calendar_ids,
    save_disabled_calendar_ids,
)


def event_view(event: CalendarEvent) -> CalendarEventView:
    """Convert a domain event to an immutable presentation value."""
    return CalendarEventView(
        event.account_id,
        event.calendar_id,
        event.event_id,
        event.title,
        event.starts_at,
        event.ends_at,
        event.all_day,
        event.location,
        event.recurrence_id,
    )


def read_agenda(
    future: Future[AgendaSnapshot],
    controller: CalendarQueryIf,
    day: date,
    days: int,
    health: Callable[[], CalendarHealthView],
) -> None:
    """Complete an agenda request without retaining a frontend."""
    if not future.set_running_or_notify_cancel():
        return
    try:
        groups = tuple(
            AgendaDayView(group.day, tuple(event_view(event) for event in group.events))
            for group in controller.load(day, days)
        )
        future.set_result(AgendaSnapshot(groups, health()))
    except Exception as error:
        future.set_exception(error)


class CalendarAgendaPresentation(CalendarAgendaIf):
    """Single-flight agenda adapter with latest-request semantics."""

    def __init__(
        self,
        controller: CalendarQueryIf,
        health: Callable[[], CalendarHealthView],
    ) -> None:
        self._controller = controller
        self._health = health
        self._future: Future[AgendaSnapshot] | None = None
        self._pending: tuple[date, int] | None = None
        self._closed = False

    def request(self, day: date, days: int) -> None:
        """Queue the latest requested window."""
        if self._closed:
            raise RuntimeError("Calendar agenda session is closed")
        if not 1 <= days <= 31:
            raise ValueError("Agenda window must contain 1 to 31 days")
        self._pending = (day, days)
        if self._future is None:
            self._start()

    def _start(self) -> None:
        if self._pending is None:
            return
        day, days = self._pending
        self._pending = None
        future: Future[AgendaSnapshot] = Future()
        self._future = future
        Thread(
            target=read_agenda,
            args=(future, self._controller, day, days, self._health),
            name="calendar-agenda-read",
            daemon=True,
        ).start()

    def poll(self) -> AgendaSnapshot | None:
        """Collect the latest result, discarding superseded reads."""
        future = self._future
        if self._closed or future is None or not future.done():
            return None
        self._future = None
        if self._pending is not None:
            self._start()
            return None
        return future.result()

    def close(self) -> None:
        """Retire the session without waiting for disk I/O."""
        self._closed = True
        self._pending = None
        if self._future is not None:
            self._future.cancel()
            self._future = None


class CalendarSelectionPresentation(CalendarSelectionIf):
    """Adapt persistent calendar selection to the UI contract."""

    def __init__(self, selection: Path, catalog: Path) -> None:
        self._selection = selection
        self._catalog = catalog

    def list_calendars(self) -> tuple[CalendarSelectionView, ...]:
        """Read discovered calendars and current selections."""
        disabled = load_disabled_calendar_ids(self._selection)
        return tuple(
            CalendarSelectionView(key, name, key not in disabled)
            for key, name in load_calendar_catalog(self._catalog).items()
        )

    def apply_selection(self, enabled: dict[str, bool]) -> None:
        """Apply all changes in one persistent update."""
        disabled = set(load_disabled_calendar_ids(self._selection))
        for key, selected in enabled.items():
            if selected:
                disabled.discard(key)
            else:
                disabled.add(key)
        save_disabled_calendar_ids(self._selection, disabled)


def calendar_health_view(path: Path | None = None) -> CalendarHealthView:
    """Translate synchronization diagnostics into presentation state."""
    health = sample_calendar_health(path)
    status = health.get("status")
    age = health.get("last_data_refresh_age_seconds")
    return CalendarHealthView(
        status=status if isinstance(status, str) else "unavailable",
        stale=bool(health.get("stale", False)),
        last_data_refresh_age_seconds=float(age) if isinstance(age, (int, float)) else None,
    )
