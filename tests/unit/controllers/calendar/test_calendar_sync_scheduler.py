# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Offline provider and periodic sync tests."""

import threading
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest

from controllers.calendar.cached_calendar_provider import CachedCalendarProvider
from controllers.calendar.calendar_controller import CalendarController
from controllers.calendar.calendar_event_cache import CalendarEventCache
from controllers.calendar.calendar_models import CalendarEvent
from controllers.calendar.calendar_sync_scheduler import CalendarSyncScheduler

NOW = datetime(2026, 11, 23, tzinfo=timezone.utc)


def test_offline_provider_filters_accounts(tmp_path) -> None:
    cache = CalendarEventCache(tmp_path / "events.sqlite3")
    start, end = NOW, NOW + timedelta(days=1)
    for account in ("one", "two"):
        cache.replace_calendar_window(
            account,
            "calendar",
            start,
            end,
            [
                CalendarEvent(
                    account_id=account,
                    calendar_id="calendar",
                    event_id="event",
                    title="Test",
                    starts_at=start + timedelta(hours=1),
                    ends_at=start + timedelta(hours=2),
                )
            ],
        )
    controller = CalendarController({"one": CachedCalendarProvider("one", cache)})
    assert len(controller.list_events(start, end)) == 1
    assert controller.list_events(start, end)[0].account_id == "one"


def test_scheduler_runs_immediately_and_stops() -> None:
    stop = threading.Event()
    worker = Mock()
    worker.sync_once.side_effect = lambda *_: stop.set()
    scheduler = CalendarSyncScheduler(
        worker,
        interval_seconds=10,
        past_days=2,
        future_days=5,
        clock=lambda: NOW,
    )
    scheduler.run(stop)
    worker.sync_once.assert_called_once_with(NOW - timedelta(days=2), NOW + timedelta(days=5))


def test_scheduler_isolates_failures() -> None:
    stop = threading.Event()
    worker = Mock()

    def fail_then_stop(*_args) -> None:
        stop.set()
        raise RuntimeError("network offline")

    worker.sync_once.side_effect = fail_then_stop
    CalendarSyncScheduler(worker, clock=lambda: NOW).run(stop)
    assert worker.sync_once.call_count == 1


def test_scheduler_rejects_invalid_configuration() -> None:
    with pytest.raises(ValueError):
        CalendarSyncScheduler(Mock(), interval_seconds=0)
