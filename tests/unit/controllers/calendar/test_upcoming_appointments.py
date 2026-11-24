# SPDX-License-Identifier: MIT
"""Upcoming appointment selection and worker regression tests."""

from concurrent.futures import Future
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from controllers.calendar.upcoming_appointments import upcoming_appointments
from frontends.tk.calendar.upcoming_panel import _read

NOW = datetime(2026, 11, 24, 12, tzinfo=timezone.utc)


def _event(minutes, *, all_day=False, recurrence_id=None):
    return SimpleNamespace(
        account_id="account",
        calendar_id="calendar",
        event_id="event",
        recurrence_id=recurrence_id,
        starts_at=NOW + timedelta(minutes=minutes),
        all_day=all_day,
    )


def test_upcoming_filters_sorts_and_deduplicates():
    first = _event(10, recurrence_id="first")
    second = _event(30, recurrence_id="second")
    controller = Mock()
    controller.load.return_value = [
        SimpleNamespace(events=[second, _event(-10), _event(0, all_day=True), first]),
        SimpleNamespace(events=[first]),
    ]
    assert upcoming_appointments(controller, NOW) == (first, second)
    assert upcoming_appointments(controller, NOW, limit=1) == (first,)
    controller.load.assert_called_with(NOW.date(), 7)


def test_upcoming_rejects_invalid_inputs():
    with pytest.raises(ValueError, match="timezone-aware"):
        upcoming_appointments(Mock(), NOW.replace(tzinfo=None))
    with pytest.raises(ValueError, match="positive"):
        upcoming_appointments(Mock(), NOW, limit=0)


def test_cancelled_worker_does_not_read_cache():
    future = Future()
    future.cancel()
    load = Mock()
    _read(future, load)
    load.assert_not_called()


def test_worker_reports_failure():
    future = Future()
    _read(future, Mock(side_effect=OSError("cache unavailable")))
    with pytest.raises(OSError, match="cache unavailable"):
        future.result()


def test_worker_returns_snapshot():
    future = Future()
    snapshot = ((), {"status": "unavailable"})
    _read(future, Mock(return_value=snapshot))
    assert future.result() == snapshot
