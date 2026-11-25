# SPDX-License-Identifier: MIT
"""Regression coverage for calendar domain boundaries."""

import ast
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from controllers.calendar.calendar_models import CalendarEvent
from controllers.calendar.calendar_query_if import AgendaDay, CalendarQueryIf
from controllers.calendar.upcoming_appointments import upcoming_appointments
from controllers.navigation.appointment_journey import AppointmentJourneyPlanner
from ui.navigation.map_ui_if import GeoPoint


class FakeCalendar:
    def __init__(self, event: CalendarEvent) -> None:
        self.event = event

    def load(self, first_day: date, days: int = 7) -> tuple[AgendaDay, ...]:
        return (AgendaDay(first_day, (self.event,)),)


def test_calendar_does_not_import_system_or_navigation_controllers():
    root = Path(__file__).resolve().parents[4]
    for path in (root / "controllers/calendar").glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            assert not any(
                name.startswith(("controllers.system", "controllers.navigation"))
                for name in names
            ), path


def test_journey_uses_calendar_contract_and_arrival_buffer():
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
    query: CalendarQueryIf = FakeCalendar(event)
    origin = GeoPoint(0.1, 0.2)
    destination = GeoPoint(0.3, 0.4)
    assert upcoming_appointments(query, now) == (event,)
    planner = AppointmentJourneyPlanner(
        query, lambda location: (destination,), lambda start, end: 1200
    )
    journey = planner.plan(now, origin)
    assert journey is not None
    assert journey.destination == destination
    assert journey.leave_by == now + timedelta(minutes=30)
    assert planner.plan(now, None) is None


def test_ambiguous_destination_never_estimates_route():
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

    def estimate(start, end):
        raise AssertionError("Ambiguous destination must not be routed")

    planner = AppointmentJourneyPlanner(
        FakeCalendar(event),
        lambda location: (GeoPoint(0.1, 0.2), GeoPoint(0.3, 0.4)),
        estimate,
    )
    assert planner.plan(now, GeoPoint(0.0, 0.0)) is None
