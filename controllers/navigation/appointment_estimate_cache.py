# SPDX-License-Identifier: MIT
"""Cache policy for local appointment journey estimates."""

from collections.abc import Callable
from math import cos, hypot, pi
from time import monotonic

from controllers.calendar.calendar_models import CalendarEvent
from controllers.calendar.calendar_query_if import CalendarQueryIf
from ui.calendar.calendar_models import AppointmentJourneyView
from ui.navigation.map_ui_if import GeoPoint


class AppointmentEstimateCache:
    """Throttle repeated local route estimates in the single monitor worker."""

    def __init__(
        self,
        *,
        position: Callable[[], GeoPoint | None],
        arrival_minutes: Callable[[], int],
        calculate: Callable[
            [CalendarQueryIf, CalendarEvent, GeoPoint, int], AppointmentJourneyView | None
        ],
        clock: Callable[[], float] = monotonic,
    ) -> None:
        self._position = position
        self._arrival_minutes = arrival_minutes
        self._calculate = calculate
        self._clock = clock
        self._event: CalendarEvent | None = None
        self._origin: GeoPoint | None = None
        self._estimate: AppointmentJourneyView | None = None
        self._expires = 0.0
        self._buffer_minutes: int | None = None

    def estimate(
        self, query: CalendarQueryIf, event: CalendarEvent
    ) -> AppointmentJourneyView | None:
        """Reuse recent estimates until the event or vehicle position changes."""
        origin = self._position()
        if origin is None or not event.location:
            self._event = None
            self._origin = None
            self._buffer_minutes = None
            self._expires = 0.0
            self._estimate = None
            return None
        buffer_minutes = self._arrival_minutes()
        now = self._clock()
        previous = self._origin
        if (
            event == self._event
            and buffer_minutes == self._buffer_minutes
            and previous is not None
            and now < self._expires
            and hypot(
                origin.latitude_rad - previous.latitude_rad,
                ((origin.longitude_rad - previous.longitude_rad + pi) % (2 * pi) - pi)
                * cos((origin.latitude_rad + previous.latitude_rad) / 2),
            )
            < 0.00004
        ):
            return self._estimate
        self._estimate = self._calculate(query, event, origin, buffer_minutes)
        self._buffer_minutes = buffer_minutes
        self._event = event
        self._origin = origin
        self._expires = self._clock() + (120 if self._estimate is not None else 30)
        return self._estimate
