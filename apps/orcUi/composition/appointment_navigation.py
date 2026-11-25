# SPDX-License-Identifier: MIT
"""Compose local-only appointment journey estimates in the monitor worker."""

import sqlite3
from time import monotonic
from math import cos, hypot, pi

import requests

from common.app_settings import AppSettingsStore
from common.navigation_data import navigation_data_root
from controllers.calendar.calendar_presentation import event_view
from controllers.calendar.calendar_models import CalendarEvent
from ui.navigation.map_ui_if import GeoPoint
from controllers.calendar.calendar_query_if import CalendarQueryIf
from controllers.navigation.appointment_journey import AppointmentJourneyPlanner
from controllers.navigation.appointment_route_estimator import (
    estimate_appointment_route,
    resolve_appointment_address,
)
from controllers.navigation.current_position import get_current_position
from controllers.navigation.sqlite_geocoder import SqliteGeocoder
from controllers.route_planning.valhalla_route_planning_controller import (
    ValhallaRoutePlanningController,
)
from protocols.valhalla.valhalla_http_client import ValhallaHttpClient
from ui.calendar.calendar_models import AppointmentJourneyView


def estimate_upcoming_journey(
    query: CalendarQueryIf, event: CalendarEvent, origin: GeoPoint, buffer_minutes: int = 10
) -> AppointmentJourneyView | None:
    """Estimate a journey using only installed local navigation resources."""
    try:
        geocoder = SqliteGeocoder(
            navigation_data_root() / "maps/search/openroadcode-search.sqlite"
        )
        try:
            router = ValhallaRoutePlanningController(ValhallaHttpClient())
            planner = AppointmentJourneyPlanner(
                query,
                lambda location: resolve_appointment_address(geocoder, location),
                lambda start, end: estimate_appointment_route(router, start, end),
                arrival_buffer_seconds=buffer_minutes * 60,
            )
            journey = planner.plan_event(event, origin)
            if journey is None:
                return None
            return AppointmentJourneyView(
                journey.leave_by, journey.travel_seconds, journey.destination, event_view(journey.event)
            )
        finally:
            geocoder.close()
    except (OSError, sqlite3.Error, requests.RequestException, ValueError, RuntimeError):
        return None


class AppointmentEstimateCache:
    """Throttle repeated local route estimates in the single monitor worker."""

    def __init__(self) -> None:
        self._event: CalendarEvent | None = None
        self._origin: GeoPoint | None = None
        self._estimate: AppointmentJourneyView | None = None
        self._expires = 0.0
        self._buffer_minutes: int | None = None
        self._settings = AppSettingsStore()

    def estimate(
        self, query: CalendarQueryIf, event: CalendarEvent
    ) -> AppointmentJourneyView | None:
        """Reuse recent estimates until the event or vehicle position changes."""
        origin = get_current_position()
        if origin is None or not event.location:
            self._event = None
            self._estimate = None
            return None
        buffer_minutes = self._settings.load().appointment_arrival_minutes
        now = monotonic()
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
            ) < 0.00004
        ):
            return self._estimate
        self._estimate = estimate_upcoming_journey(query, event, origin, buffer_minutes)
        self._buffer_minutes = buffer_minutes
        self._event = event
        self._origin = origin
        self._expires = monotonic() + (120 if self._estimate is not None else 30)
        return self._estimate
