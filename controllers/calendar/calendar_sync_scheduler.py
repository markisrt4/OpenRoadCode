# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Interruptible periodic calendar synchronization.

Run on a dedicated background thread or process; never the UI thread.
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from .calendar_sync_health import CalendarSyncHealth
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
        health: CalendarSyncHealth | None = None,
        online_allowed: Callable[[], bool] | None = None,
    ) -> None:
        if interval_seconds <= 0 or past_days < 0 or future_days <= 0:
            raise ValueError("Invalid synchronization interval or window")
        self._worker = worker
        self._online_allowed = online_allowed or (lambda: True)
        self._health = health
        self._interval = interval_seconds
        self._past_days = past_days
        self._future_days = future_days
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def run(self, stop: threading.Event) -> None:
        """Sync immediately, then wait between attempts until stopped."""
        startup_delays = iter((5, 10, 20, 30))
        startup = True
        while not stop.is_set():
            if not self._online_allowed():
                stop.wait(1.0)
                continue
            attempted = datetime.now(timezone.utc)
            started = time.monotonic()
            result = None
            try:
                now = self._clock()
                if now.tzinfo is None:
                    raise ValueError("Clock must return an aware datetime")
                _LOG.info("Calendar synchronization started")
                result = self._worker.sync_once(
                    now - timedelta(days=self._past_days),
                    now + timedelta(days=self._future_days),
                )
                _LOG.info(
                    "Calendar synchronization completed: cached=%d failed=%d disabled=%d elapsed=%.1fs",
                    result.cached_calendars,
                    sum(not status.ok and not status.disabled for status in result.statuses),
                    sum(status.disabled for status in result.statuses),
                    time.monotonic() - started,
                )
            except Exception:  # noqa: BLE001 - isolate background sync failures
                _LOG.exception("Calendar sync failed; cached events retained")
            if self._health is not None:
                try:
                    self._health.record(
                        attempted,
                        datetime.now(timezone.utc),
                        time.monotonic() - started,
                        self._interval,
                        result,
                    )
                except OSError:
                    _LOG.exception("Unable to publish calendar synchronization health")
            delay = self._interval
            if startup and result is None:
                delay = next(startup_delays, self._interval)
                if delay == self._interval:
                    startup = False
                else:
                    _LOG.info("Retrying calendar startup in %s seconds", delay)
            else:
                startup = False
            deadline = time.monotonic() + delay
            while not stop.is_set() and self._online_allowed():
                remaining = deadline - time.monotonic()
                if remaining <= 0 or stop.wait(min(1.0, remaining)):
                    break
