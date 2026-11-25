# SPDX-License-Identifier: MIT
"""Compose local-only appointment journey estimates in the monitor worker."""

import sqlite3
from datetime import datetime

import requests

from common.navigation_data import navigation_data_root
from controllers.calendar.calendar_presentation import event_view
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
    query: CalendarQueryIf, now: datetime
) -> AppointmentJourneyView | None:
    """Estimate a journey using only installed local navigation resources."""
    origin = get_current_position()
    if origin is None:
        return None
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
            )
            journey = planner.plan(now, origin)
            if journey is None:
                return None
            return AppointmentJourneyView(
                journey.leave_by, journey.travel_seconds, journey.destination, event_view(journey.event)
            )
        finally:
            geocoder.close()
    except (OSError, sqlite3.Error, requests.RequestException, ValueError, RuntimeError):
        return None
