# SPDX-License-Identifier: MIT
"""Deterministic tests for the appointment monitor."""

from unittest.mock import Mock, patch

import pytest

from controllers.calendar.appointment_monitor import AppointmentMonitor
from ui.calendar.calendar_models import AppointmentSnapshot, CalendarHealthView


def test_monitor_single_flight_and_refresh_interval():
    clock = Mock(return_value=0)
    monitor = AppointmentMonitor(Mock(), clock=clock)
    with patch("controllers.calendar.appointment_monitor.Thread") as thread:
        monitor.poll()
        monitor.poll()
        assert thread.call_count == 1
        monitor._future.set_result(AppointmentSnapshot((), CalendarHealthView()))
        monitor.poll()
        assert monitor.snapshot == AppointmentSnapshot((), CalendarHealthView())
        clock.return_value = 29
        monitor.poll()
        assert thread.call_count == 1
        clock.return_value = 30
        monitor.poll()
        assert thread.call_count == 2


def test_monitor_retains_snapshot_and_recovers():
    clock = Mock(return_value=0)
    monitor = AppointmentMonitor(Mock(), clock=clock)
    with patch("controllers.calendar.appointment_monitor.Thread"):
        monitor.poll()
        monitor._future.set_result(AppointmentSnapshot((), CalendarHealthView(status="degraded")))
        monitor.poll()
        clock.return_value = 30
        monitor.poll()
        monitor._future.set_exception(OSError("cache unavailable"))
        monitor.poll()
        assert monitor.failed
        assert monitor.snapshot == AppointmentSnapshot((), CalendarHealthView(status="degraded"))
        clock.return_value = 60
        monitor.poll()
        monitor._future.set_result(AppointmentSnapshot((), CalendarHealthView(status="ok")))
        monitor.poll()
        assert not monitor.failed
        assert monitor.snapshot == AppointmentSnapshot((), CalendarHealthView(status="ok"))


def test_monitor_close_cancels_pending_read():
    monitor = AppointmentMonitor(Mock(), clock=lambda: 0)
    with patch("controllers.calendar.appointment_monitor.Thread") as thread:
        monitor.poll()
        future = monitor._future
        monitor.close()
        assert future.cancelled()
        assert monitor._future is None

        monitor.poll()
        assert thread.call_count == 1


@pytest.mark.parametrize("interval", [0, -1, float("inf"), float("nan")])
def test_invalid_monitor_interval(interval):
    with pytest.raises(ValueError, match="interval"):
        AppointmentMonitor(Mock(), interval=interval)


def test_monitor_retries_after_worker_start_failure():
    clock = Mock(return_value=0)
    monitor = AppointmentMonitor(Mock(), clock=clock)
    with patch("controllers.calendar.appointment_monitor.Thread") as thread:
        thread.return_value.start.side_effect = RuntimeError("thread unavailable")
        monitor.poll()
        assert monitor.failed
        assert monitor._future is None
        monitor.poll()
        assert thread.call_count == 1
        clock.return_value = 30
        thread.return_value.start.side_effect = None
        monitor.poll()
        assert thread.call_count == 2
        monitor._future.set_result(AppointmentSnapshot((), CalendarHealthView()))
        monitor.poll()
        assert not monitor.failed
