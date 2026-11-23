# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Interruptible periodic calendar synchronization.

Run on a dedicated background thread or process; never the UI thread.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from .calendar_sync_worker import CalendarSyncWorker

_LOG = logging.getLogger(__name__)


class CalendarSyncScheduler:
    """Periodically refresh a bounded UTC window; retain cache on failures."""

    def __init__(
        self,
        worker: CalendarSyncWorker,
        *,
        interval_seconds: float = 900,
        past_days: int = 7,
        future_days: int = 30,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if interval_seconds <= 0 or past_days < 0 or future_days <= 0:
            raise ValueError("Invalid synchronization interval or window")
        self._worker = worker
        self._interval = interval_seconds
        self._past_days = past_days
        self._future_days = future_days
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def run(self, stop: threading.Event) -> None:
        """Sync immediately, then wait between attempts until stopped."""
        while not stop.is_set():
            try:
                now = self._clock()
                if now.tzinfo is None:
                    raise ValueError("Clock must return an aware datetime")
                self._worker.sync_once(
                    now - timedelta(days=self._past_days),
                    now + timedelta(days=self._future_days),
                )
            except Exception:
                _LOG.exception("Calendar sync failed; cached events retained")
            if stop.wait(self._interval):
                break
