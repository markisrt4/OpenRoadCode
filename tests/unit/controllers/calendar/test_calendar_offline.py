# SPDX-License-Identifier: MIT
"""Exercise offline calendar and journey adapters without network services."""

from datetime import datetime, timedelta, timezone
from math import radians
from unittest.mock import Mock

from controllers.calendar.cached_calendar_provider import CachedCalendarProvider
from controllers.calendar.calendar_event_cache import CalendarEventCache
from controllers.calendar.calendar_models import CalendarEvent
from controllers.navigation.appointment_route_estimator import (
    estimate_appointment_route,
    resolve_appointment_address,
)
from controllers.navigation.geocoding_models import GeocodeResult
from controllers.route_planning.route_planning_types import GeoPoint as RoutePoint, RouteRequest
from ui.navigation.map_ui_if import GeoPoint


def test_cached_appointments_survive_provider_unavailability(tmp_path):
    now = datetime(2026, 11, 25, 12, tzinfo=timezone.utc)
    event = CalendarEvent(
        "account",
        "calendar",
        "event",
        "Appointment",
        now + timedelta(hours=1),
        now + timedelta(hours=2),
        location="Office",
    )
    path = tmp_path / "events.sqlite3"
    cache = CalendarEventCache(path)
    cache.replace_calendar_window("account", "calendar", now, now + timedelta(days=7), [event])
    offline = CachedCalendarProvider("account", CalendarEventCache(path))
    assert offline.list_events(now, now + timedelta(days=1)) == [event]


def test_offline_resolver_rejects_street_fallback():
    geocoder = Mock()
    point = GeoPoint(0.1, 0.2)
    geocoder.geocode.return_value = (GeocodeResult("Street", point, 0.8, "street"),)
    assert resolve_appointment_address(geocoder, "123 Street") == ()
    geocoder.geocode.return_value = (GeocodeResult("Address", point, 1.0, "address"),)
    assert resolve_appointment_address(geocoder, "123 Street") == (point,)


def test_route_estimation_uses_degree_coordinates():
    router = Mock()
    router.calculate_route.return_value.duration_seconds = 1200.0
    origin = GeoPoint(radians(45), radians(-90))
    destination = GeoPoint(radians(0), radians(90))
    assert estimate_appointment_route(router, origin, destination) == 1200.0
    router.calculate_route.assert_called_once_with(
        RouteRequest(RoutePoint(45, -90), RoutePoint(0, 90))
    )
