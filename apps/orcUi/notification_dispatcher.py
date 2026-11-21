# SPDX-License-Identifier: MIT
"""Composition-owned notification delivery and flood protection."""
from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable

from ui.notification_if import Notification, NotificationSeverity


class NotificationDispatcher:
    """Thread-safe sink; only the supplied UI callback touches presentation."""

    def __init__(self, run_ui: Callable[[Callable[[], None]], None],
                 present: Callable[[Notification], None], *,
                 cooldown_seconds: float = 5.0,
                 clock: Callable[[], float] = time.monotonic) -> None:
        self._run_ui = run_ui
        self._present = present
        self._cooldown = cooldown_seconds
        self._clock = clock
        self._lock = threading.Lock()
        self._recent: dict[tuple[str, str], float] = {}
        self._logger = logging.getLogger("orc.notifications")

    def publish(self, notification: Notification) -> None:
        """Log every event, but suppress repeated on-screen notifications."""
        self._logger.log(
            logging.ERROR if notification.severity in (
                NotificationSeverity.ERROR, NotificationSeverity.CRITICAL,
            ) else logging.WARNING if notification.severity is NotificationSeverity.WARNING
            else logging.INFO,
            "%s [%s]: %s", notification.source, notification.code, notification.message,
        )
        key = (notification.source, notification.code)
        with self._lock:
            now = self._clock()
            if now - self._recent.get(key, float("-inf")) < self._cooldown:
                return
            self._recent[key] = now
            if len(self._recent) > 256:
                self._recent = {k: t for k, t in self._recent.items()
                                if now - t < self._cooldown}
        self._run_ui(lambda: self._present(notification))
