# SPDX-License-Identifier: MIT
"""Calendar UI ports; implementations own persistence and background work."""

from datetime import date
from typing import Protocol

from .calendar_models import AgendaSnapshot, AppointmentSnapshot, CalendarSelectionView


class CalendarAgendaIf(Protocol):
    """Nonblocking agenda request and collection contract."""

    def request(self, day: date, days: int) -> None:
        """Request a bounded agenda window."""

    def poll(self) -> AgendaSnapshot | None:
        """Return a completed snapshot, or None while pending."""

    def close(self) -> None:
        """Retire pending work without blocking the UI."""


class CalendarSelectionIf(Protocol):
    """Calendar discovery and selection contract."""

    def list_calendars(self) -> tuple[CalendarSelectionView, ...]:
        """Return discovered calendars and their enabled state."""

    def apply_selection(self, enabled: dict[str, bool]) -> None:
        """Atomically persist selections while preserving unknown calendar IDs."""


class AppointmentMonitorIf(Protocol):
    """Nonblocking upcoming appointment state contract."""

    @property
    def snapshot(self) -> AppointmentSnapshot | None:
        """Return the most recent completed snapshot."""

    @property
    def failed(self) -> bool:
        """Indicate whether the latest read failed."""

    def poll(self) -> None:
        """Advance background refresh without blocking."""

    def close(self) -> None:
        """Retire pending refresh work."""


class CalendarPresentationIf(Protocol):
    """Aggregate calendar ports for an agenda presentation session."""

    @property
    def agenda(self) -> CalendarAgendaIf:
        """Return the agenda request port."""

    @property
    def selection(self) -> CalendarSelectionIf:
        """Return the calendar selection port."""

    def close(self) -> None:
        """Release presentation session resources."""
