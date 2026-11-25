# SPDX-License-Identifier: MIT
"""Plan appointment departures without changing active navigation."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from math import isfinite

from controllers.calendar.calendar_models import CalendarEvent
from controllers.calendar.calendar_query_if import CalendarQueryIf
from controllers.calendar.upcoming_appointments import upcoming_appointments
from ui.navigation.map_ui_if import GeoPoint


@dataclass(frozen=True)
class AppointmentJourney:
    """A resolved appointment and its estimated departure time."""

    event: CalendarEvent
    destination: GeoPoint
    travel_seconds: float
    leave_by: datetime


class AppointmentJourneyPlanner:
    """Use injected destination resolution and non-mutating route estimates."""

    def __init__(
        self,
        calendar: CalendarQueryIf,
        resolve: Callable[[str], tuple[GeoPoint, ...]],
        estimate: Callable[[GeoPoint, GeoPoint], float | None],
        *,
        arrival_buffer_seconds: float = 600,
    ) -> None:
        if not isfinite(arrival_buffer_seconds) or arrival_buffer_seconds < 0:
            raise ValueError("Arrival buffer must be finite and nonnegative")
        self._calendar = calendar
        self._resolve = resolve
        self._estimate = estimate
        self._buffer = arrival_buffer_seconds

    def plan(self, now: datetime, origin: GeoPoint | None) -> AppointmentJourney | None:
        """Estimate the next appointment without starting guidance.

        @param now Current timezone-aware time.
        @param origin Current position, or None when unavailable.
        @return Journey when the destination and travel estimate are available.
        """
        if origin is None:
            return None
        events = upcoming_appointments(self._calendar, now, limit=1)
        if not events:
            return None
        event = events[0]
        location = (event.location or "").strip()
        if not location:
            return None
        candidates = self._resolve(location)
        if len(candidates) != 1:
            return None
        destination = candidates[0]
        seconds = self._estimate(origin, destination)
        if seconds is None or not isfinite(seconds) or seconds < 0:
            return None
        departure = event.starts_at.astimezone(timezone.utc) - timedelta(
            seconds=seconds + self._buffer
        )
        return AppointmentJourney(
            event, destination, seconds, departure.astimezone(event.starts_at.tzinfo)
        )
