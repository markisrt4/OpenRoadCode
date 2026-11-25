# SPDX-License-Identifier: MIT
"""Regression tests for appointment route estimate reuse."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

from controllers.navigation.appointment_estimate_cache import AppointmentEstimateCache
from common.app_settings import AppSettings
from controllers.calendar.calendar_models import CalendarEvent
from ui.navigation import GeoPoint


def test_estimate_cache_invalidates_on_inputs_and_expiration():
    now = datetime.now(timezone.utc)
    event = CalendarEvent(
        "account", "calendar", "event", "Appointment",
        now + timedelta(hours=1), now + timedelta(hours=2), location="Address",
    )
    clock = Mock(return_value=0.0)
    position = Mock(return_value=GeoPoint(0.7, -1.4))
    estimate = Mock(return_value=Mock())
    settings = Mock()
    settings.load.return_value = AppSettings()
    cache = AppointmentEstimateCache(
        position=position,
        arrival_minutes=lambda: settings.load().appointment_arrival_minutes,
        calculate=estimate,
        clock=clock,
    )
    query = Mock()

    first = cache.estimate(query, event)
    assert cache.estimate(query, event) is first
    assert estimate.call_count == 1
    clock.return_value = 121.0
    cache.estimate(query, event)
    assert estimate.call_count == 2
    settings.load.return_value = AppSettings(appointment_arrival_minutes=20)
    cache.estimate(query, event)
    assert estimate.call_count == 3
    position.return_value = GeoPoint(0.701, -1.4)
    cache.estimate(query, event)
    assert estimate.call_count == 4
    cache.estimate(query, replace(event, location="New address"))
    assert estimate.call_count == 5
    position.return_value = None
    assert cache.estimate(query, event) is None
    position.return_value = GeoPoint(0.701, -1.4)
    cache.estimate(query, event)
    assert estimate.call_count == 6
