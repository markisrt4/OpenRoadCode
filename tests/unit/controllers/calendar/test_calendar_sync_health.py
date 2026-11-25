# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Regression coverage for persistent calendar health."""

from datetime import datetime, timedelta, timezone

from controllers.calendar.caldav_provider import CalendarSyncStatus
from controllers.calendar.calendar_sync_health import CalendarSyncHealth
from controllers.calendar.calendar_sync_worker import CalendarSyncResult

NOW = datetime(2026, 11, 24, tzinfo=timezone.utc)


def test_health_retains_success_across_failures(tmp_path) -> None:
    path = tmp_path / "events.health.json"
    health = CalendarSyncHealth(path)
    assert health.read() == {}
    result = CalendarSyncResult((CalendarSyncStatus("private", True, event_count=45),), 1)
    health.record(NOW, NOW, 5.9, 900, result)
    success = health.read()
    assert success["status"] == "ok"
    assert success["metrics"]["synced_events"] == 45
    assert "private" not in path.read_text()
    later = NOW + timedelta(minutes=15)
    CalendarSyncHealth(path).record(later, later, 2, 900, None)
    failed = health.read()
    assert failed["status"] == "failed"
    assert failed["last_attempt"] == later.isoformat()
    assert failed["last_success"] == success["last_success"]
    assert failed["last_success_metrics"] == success["metrics"]


def test_partial_sync_is_degraded(tmp_path) -> None:
    health = CalendarSyncHealth(tmp_path / "health.json")
    result = CalendarSyncResult(
        (
            CalendarSyncStatus("one", True, event_count=3, skipped_resources=1),
            CalendarSyncStatus("two", False),
            CalendarSyncStatus("three", False, disabled=True),
        ),
        1,
    )
    health.record(NOW, NOW, 1, 900, result)
    snapshot = health.read()
    assert snapshot["status"] == "degraded"
    assert snapshot["last_success"] is None
    assert snapshot["metrics"] == {
        "cached_calendars": 1,
        "failed_calendars": 1,
        "disabled_calendars": 1,
        "synced_events": 3,
        "skipped_resources": 1,
    }


def test_corrupt_health_is_unavailable(tmp_path) -> None:
    path = tmp_path / "health.json"
    path.write_text("{")
    assert CalendarSyncHealth(path).read() == {}
