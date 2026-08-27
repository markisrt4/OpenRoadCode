# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Publish the latest browser position at a steady application cadence."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from threading import Event, Lock, Thread

from controllers.navigation.navigation_state import PositionState


PositionStateSink = Callable[[PositionState], None]


class PeriodicPositionPublisher:
    """Publish the latest position at a fixed rate with cache semantics.

    A newly received sensor fix is published once with ``is_cached=False``.
    Subsequent publications of that same fix use ``is_cached=True`` until a
    newer sensor fix is supplied.
    """

    def __init__(self, sink: PositionStateSink, *, rate_hz: float = 5.0) -> None:
        if rate_hz <= 0.0:
            raise ValueError("rate_hz must be greater than zero")
        self._sink = sink
        self._period_s = 1.0 / rate_hz
        self._lock = Lock()
        self._latest: PositionState | None = None
        self._generation = 0
        self._published_generation = -1
        self._stop_event = Event()
        self._thread = Thread(
            target=self._run,
            name="periodic-position-publisher",
            daemon=True,
        )

    def start(self) -> None:
        if not self._thread.is_alive():
            self._thread.start()

    def update(self, state: PositionState) -> None:
        """Store the newest sensor fix for publication."""
        with self._lock:
            self._latest = replace(state, is_cached=False)
            self._generation += 1

    def publish_once(self) -> bool:
        """Publish the latest state once; return False when no state exists."""
        with self._lock:
            state = self._latest
            generation = self._generation
            is_cached = generation == self._published_generation

        if state is None:
            return False

        self._sink(replace(state, is_cached=is_cached))

        with self._lock:
            if self._generation == generation:
                self._published_generation = generation
        return True

    def close(self) -> None:
        self._stop_event.set()
        if self._thread.is_alive():
            self._thread.join(timeout=max(1.0, self._period_s * 2.0))

    def _run(self) -> None:
        while not self._stop_event.wait(self._period_s):
            self.publish_once()
