# SPDX-License-Identifier: MIT
"""Exercise offline synchronization transitions without network access."""

from threading import Event
from unittest.mock import Mock

from controllers.calendar.calendar_sync_scheduler import CalendarSyncScheduler


def test_offline_scheduler_does_not_contact_provider():
    worker = Mock()
    stop = Mock(spec=Event)
    stop.is_set.side_effect = [False, True]
    scheduler = CalendarSyncScheduler(worker, online_allowed=lambda: False)
    scheduler.run(stop)
    worker.sync_once.assert_not_called()
    stop.wait.assert_called_once_with(1.0)


def test_scheduler_resumes_when_online():
    worker = Mock()
    stop = Event()
    online = False

    def allowed():
        nonlocal online
        previous = online
        online = True
        return previous

    worker.sync_once.side_effect = lambda *args: stop.set()
    scheduler = CalendarSyncScheduler(worker, online_allowed=allowed)
    scheduler.run(stop)
    worker.sync_once.assert_called_once()
