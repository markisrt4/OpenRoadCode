# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""SQLite cache behavior and failure-isolated synchronization."""

from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest

from controllers.calendar.caldav_provider import CalendarSyncStatus
from controllers.calendar.calendar_event_cache import CalendarEventCache
from controllers.calendar.calendar_models import CalendarEvent
from controllers.calendar.calendar_sync_worker import CalendarSyncWorker
from controllers.calendar.icalendar_parser import parse_icalendar_events

START = datetime(2026, 11, 23, tzinfo=timezone.utc)
END = START + timedelta(days=1)


def event(event_id: str, calendar_id: str = "calendar-a") -> CalendarEvent:
    return CalendarEvent(
        account_id="account",
        calendar_id=calendar_id,
        event_id=event_id,
        title="Test event",
        starts_at=START + timedelta(hours=2),
        ends_at=START + timedelta(hours=3),
    )


def test_cache_round_trip_and_empty_replacement(tmp_path) -> None:
    cache = CalendarEventCache(tmp_path / "calendar.sqlite3")
    cache.replace_calendar_window("account", "calendar-a", START, END, [event("one")])
    assert cache.list_events(START, END) == [event("one")]
    cache.replace_calendar_window("account", "calendar-a", START, END, [])
    assert cache.list_events(START, END) == []


def test_cache_rejects_cross_calendar_events(tmp_path) -> None:
    cache = CalendarEventCache(tmp_path / "calendar.sqlite3")
    with pytest.raises(ValueError):
        cache.replace_calendar_window(
            "account", "calendar-a", START, END, [event("one", "calendar-b")]
        )


def test_failed_and_disabled_calendars_preserve_cache(tmp_path) -> None:
    cache = CalendarEventCache(tmp_path / "calendar.sqlite3")
    cache.replace_calendar_window("account", "calendar-b", START, END, [event("old", "calendar-b")])
    provider = Mock()
    provider.list_events.return_value = [event("new")]
    provider.last_sync_status = [
        CalendarSyncStatus("calendar-a", True, event_count=1),
        CalendarSyncStatus("calendar-b", False, error="CalDavTimeoutError"),
        CalendarSyncStatus("calendar-c", False, disabled=True),
    ]
    result = CalendarSyncWorker("account", provider, cache).sync_once(START, END)
    assert result.cached_calendars == 1
    assert {item.event_id for item in cache.list_events(START, END)} == {"old", "new"}


def test_new_window_replaces_stale_events(tmp_path) -> None:
    cache = CalendarEventCache(tmp_path / "calendar.sqlite3")
    cache.replace_calendar_window("account", "calendar-a", START, END, [event("old")])
    next_start = START + timedelta(minutes=15)
    next_end = END + timedelta(minutes=15)
    cache.replace_calendar_window("account", "calendar-a", next_start, next_end, [event("new")])
    assert [item.event_id for item in cache.list_events(START, END)] == ["new"]


def test_new_empty_window_removes_deleted_events(tmp_path) -> None:
    cache = CalendarEventCache(tmp_path / "calendar.sqlite3")
    cache.replace_calendar_window("account", "calendar-a", START, END, [event("old")])
    cache.replace_calendar_window(
        "account", "calendar-a", START + timedelta(minutes=15), END + timedelta(minutes=15), []
    )
    assert cache.list_events(START, END) == []


def test_recurrence_snapshot_replaces_moved_and_cancelled_instances(tmp_path) -> None:
    cache = CalendarEventCache(tmp_path / "calendar.sqlite3")
    end = START + timedelta(days=4)
    master = (
        "BEGIN:VEVENT\nUID:series\nDTSTART:20261123T140000Z\n"
        "DTEND:20261123T150000Z\nRRULE:FREQ=DAILY;COUNT=3\nEND:VEVENT\n"
    )
    original = parse_icalendar_events(master, "account", "calendar-a", START, end)
    assert len(original) == 3
    for _ in range(2):
        cache.replace_calendar_window("account", "calendar-a", START, end, original)
    assert cache.list_events(START, end) == original
    overrides = (
        "BEGIN:VEVENT\nUID:series\nRECURRENCE-ID:20261124T140000Z\n"
        "DTSTART:20261124T160000Z\nDTEND:20261124T170000Z\nEND:VEVENT\n"
        "BEGIN:VEVENT\nUID:series\nRECURRENCE-ID:20261125T140000Z\n"
        "STATUS:CANCELLED\nEND:VEVENT\n"
    )
    updated = parse_icalendar_events(master + overrides, "account", "calendar-a", START, end)
    cache.replace_calendar_window("account", "calendar-a", START, end, updated)
    cached = cache.list_events(START, end)
    assert len(cached) == 2
    assert cached[1].starts_at.hour == 16
    assert cached[1].recurrence_id == original[1].recurrence_id
