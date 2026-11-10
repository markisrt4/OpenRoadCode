# SPDX-License-Identifier: MIT
"""Runtime shutdown cannot leave a late RF launch running."""
from threading import Event, Thread
from unittest.mock import Mock

import pytest

from apps.orcUi.radio_application_service import ManagedRadioApplicationService


def test_terminal_close_rejects_launch_and_stops_once():
    manager, launcher = Mock(), Mock()
    service = ManagedRadioApplicationService(manager, launcher)
    service.close()
    service.close()
    with pytest.raises(RuntimeError, match="closed"):
        service.present()
    launcher.prepare.assert_not_called()
    manager.stop.assert_called_once_with("sdrpp")


def test_shutdown_waits_for_inflight_start_and_stops_after_it():
    manager, launcher = Mock(), Mock()
    manager.is_running.return_value = False
    entered, release = Event(), Event()
    events = []
    def prepare(_display):
        entered.set()
        assert release.wait(2)
        events.append("started")
    launcher.prepare.side_effect = prepare
    manager.stop.side_effect = lambda _key: events.append("stopped")
    service = ManagedRadioApplicationService(manager, launcher)
    start = Thread(target=service.present)
    start.start()
    assert entered.wait(2)
    shutdown = Thread(target=service.close)
    shutdown.start()
    release.set()
    start.join(2)
    shutdown.join(2)
    assert not start.is_alive() and not shutdown.is_alive()
    assert events == ["started", "stopped"]
