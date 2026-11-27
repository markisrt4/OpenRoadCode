# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Regression tests for bounded calendar recurrence."""

from datetime import datetime, timezone

from controllers.calendar.icalendar_parser import parse_icalendar_events


def test_moved_and_cancelled_occurrences() -> None:
    raw = (
        "BEGIN:VEVENT\nUID:series\nDTSTART:20261123T140000Z\n"
        "DTEND:20261123T150000Z\nRRULE:FREQ=DAILY;COUNT=3\nEND:VEVENT\n"
        "BEGIN:VEVENT\nUID:series\nRECURRENCE-ID:20261124T140000Z\n"
        "DTSTART:20261124T160000Z\nDTEND:20261124T170000Z\nEND:VEVENT\n"
        "BEGIN:VEVENT\nUID:series\nRECURRENCE-ID:20261125T140000Z\n"
        "STATUS:CANCELLED\nEND:VEVENT\n"
    )
    events = parse_icalendar_events(
        raw,
        "account",
        "calendar",
        datetime(2026, 11, 23, tzinfo=timezone.utc),
        datetime(2026, 11, 27, tzinfo=timezone.utc),
    )
    assert len(events) == 2
    assert events[1].starts_at.hour == 16
    assert events[1].recurrence_id == "2026-11-24T14:00:00+00:00"


def test_excluded_and_added_occurrences() -> None:
    raw = (
        "BEGIN:VEVENT\nUID:series\nDTSTART:20261123T140000Z\n"
        "DTEND:20261123T150000Z\nRRULE:FREQ=DAILY;COUNT=3\n"
        "EXDATE:20261124T140000Z\nRDATE:20261127T140000Z\nEND:VEVENT"
    )
    events = parse_icalendar_events(
        raw,
        "account",
        "calendar",
        datetime(2026, 11, 23, tzinfo=timezone.utc),
        datetime(2026, 11, 28, tzinfo=timezone.utc),
    )
    assert [event.starts_at.day for event in events] == [23, 25, 27]
    assert len({event.recurrence_id for event in events}) == 3


def test_weekly_recurrence_preserves_local_hour_across_dst() -> None:
    raw = (
        "BEGIN:VEVENT\nUID:series\nDTSTART;TZID=America/Detroit:20261026T090000\n"
        "DTEND;TZID=America/Detroit:20261026T100000\n"
        "RRULE:FREQ=WEEKLY;COUNT=2\nEND:VEVENT"
    )
    events = parse_icalendar_events(
        raw,
        "account",
        "calendar",
        datetime(2026, 10, 25, tzinfo=timezone.utc),
        datetime(2026, 11, 4, tzinfo=timezone.utc),
    )
    assert [event.starts_at.hour for event in events] == [9, 9]
    assert [event.starts_at.astimezone(timezone.utc).hour for event in events] == [13, 14]
