# SPDX-License-Identifier: MIT
"""Toolkit-free notification delivery contract tests."""

from unittest.mock import Mock

import pytest

from apps.orcUi.notification_dispatcher import NotificationDispatcher
from ui.notification_if import Notification, NotificationSeverity


def _event(code="adsb.launch_failed", severity=NotificationSeverity.ERROR):
    return Notification(code, "ADS-B Map Unavailable", "Connection refused", severity, "adsb")


def test_event_is_immutable_and_validated():
    event = _event()
    with pytest.raises(AttributeError):
        event.message = "changed"
    with pytest.raises(ValueError, match="code"):
        Notification("", "Title", "Message", NotificationSeverity.ERROR, "radio")


def test_dispatcher_schedules_ui_and_suppresses_duplicate(caplog):
    callbacks = []
    presented = []
    clock = [10.0]
    dispatcher = NotificationDispatcher(
        callbacks.append, presented.append, cooldown_seconds=5, clock=lambda: clock[0]
    )
    dispatcher.publish(_event())
    dispatcher.publish(_event())
    assert len(callbacks) == 1
    callbacks.pop()()
    assert len(presented) == 1
    assert "Connection refused" in caplog.text
    clock[0] = 16.0
    dispatcher.publish(_event())
    assert len(callbacks) == 1


def test_distinct_codes_are_not_suppressed():
    callbacks = []
    dispatcher = NotificationDispatcher(callbacks.append, Mock(), clock=lambda: 1.0)
    dispatcher.publish(_event())
    dispatcher.publish(_event(code="adsb.browser_failed"))
    assert len(callbacks) == 2
