# SPDX-License-Identifier: MIT
"""Toolkit-independent calendar agenda query contract."""

from dataclasses import dataclass
from datetime import date
from typing import Protocol

from .calendar_models import CalendarEvent


@dataclass(frozen=True)
class AgendaDay:
    """Events visible on one local calendar date."""

    day: date
    events: tuple[CalendarEvent, ...]


class CalendarQueryIf(Protocol):
    """Read bounded local-date agenda windows without provider knowledge."""

    def load(self, first_day: date, days: int = 7) -> tuple[AgendaDay, ...]:
        """Read events grouped by local date.

        @param first_day First local date.
        @param days Number of days, from 1 to 31.
        @return Nonempty agenda days.
        """
