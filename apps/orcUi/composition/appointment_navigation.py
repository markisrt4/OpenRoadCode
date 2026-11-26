# SPDX-License-Identifier: MIT
"""Compose local-only appointment journey estimates in the monitor worker."""

import sqlite3

import requests

from common.app_settings import AppSettingsStore
from common.navigation_data import navigation_data_root
from controllers.calendar.calendar_models import CalendarEvent
from controllers.calendar.calendar_presentation import event_view
from controllers.calendar.calendar_query_if import CalendarQueryIf
from controllers.navigation.appointment_estimate_cache import AppointmentEstimateCache
from controllers.navigation.appointment_journey import AppointmentJourneyPlanner
from controllers.navigation.appointment_route_estimator import (
    estimate_appointment_route,
)
from controllers.navigation.current_position import get_current_position
from controllers.navigation.sqlite_geocoder import SqliteGeocoder
from controllers.route_planning.valhalla_route_planning_controller import (
    ValhallaRoutePlanningController,
)
from protocols.valhalla.valhalla_http_client import ValhallaHttpClient
from ui.calendar.calendar_models import AppointmentJourneyView
from ui.navigation.map_ui_if import GeoPoint


def estimate_upcoming_journey(
    query: CalendarQueryIf, event: CalendarEvent, origin: GeoPoint, buffer_minutes: int = 10
) -> AppointmentJourneyView | None:
    """Estimate a journey using only installed local navigation resources."""
    try:
        geocoder = SqliteGeocoder(navigation_data_root() / "maps/search/openroadcode-search.sqlite")
        try:
            router = ValhallaRoutePlanningController(ValhallaHttpClient())
            candidates = (
                tuple(
                    result
                    for result in geocoder.geocode((event.location or "").strip())
                    if result.source == "address"
                )
                if event.location
                else ()
            )
            if len(candidates) != 1:
                return None
            planner = AppointmentJourneyPlanner(
                query,
                lambda location: (candidates[0].position,),
                lambda start, end: estimate_appointment_route(router, start, end),
                arrival_buffer_seconds=buffer_minutes * 60,
            )
            journey = planner.plan_event(event, origin)
            if journey is None:
                return None
            return AppointmentJourneyView(
                journey.leave_by,
                journey.travel_seconds,
                journey.destination,
                event_view(journey.event),
                candidates[0].display_name,
            )
        finally:
            geocoder.close()
    except (OSError, sqlite3.Error, requests.RequestException, ValueError, RuntimeError):
        return None


def create_appointment_estimate_cache() -> AppointmentEstimateCache:
    """Wire the cache controller to local navigation and settings providers."""
    settings = AppSettingsStore()
    return AppointmentEstimateCache(
        position=get_current_position,
        arrival_minutes=lambda: settings.load().appointment_arrival_minutes,
        calculate=estimate_upcoming_journey,
    )
