# SPDX-License-Identifier: MIT
"""Single-flight cache reader shared by Home calendar consumers."""

from concurrent.futures import Future
from math import isfinite
from threading import Thread
from time import monotonic
from typing import Callable, TypeVar

from ui.calendar.calendar_models import AppointmentSnapshot

T = TypeVar("T")


def read_snapshot(future: Future[T], load: Callable[[], T]) -> None:
    if not future.set_running_or_notify_cancel():
        return
    try:
        future.set_result(load())
    except Exception as error:
        future.set_exception(error)


class AppointmentMonitor:
    """Poll from the UI thread; only the loader runs on a worker."""

    def __init__(
        self,
        load: Callable[[], AppointmentSnapshot],
        *,
        interval: float = 30,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        if not isfinite(interval) or interval <= 0:
            raise ValueError("interval must be finite and positive")
        self._load = load
        self._interval = interval
        self._clock = clock
        self._future: Future[AppointmentSnapshot] | None = None
        self._next_read = 0.0
        self.snapshot: AppointmentSnapshot | None = None
        self._closed = False
        self.failed = False

    def poll(self) -> None:
        if self._closed:
            return
        if self._future is not None:
            if not self._future.done():
                return
            try:
                self.snapshot = self._future.result()
                self.failed = False
            except Exception:
                self.failed = True
            self._future = None
            self._next_read = self._clock() + self._interval
        if self._clock() >= self._next_read:
            self._future = Future()
            try:
                Thread(
                    target=read_snapshot,
                    args=(self._future, self._load),
                    daemon=True,
                    name="upcoming-calendar-read",
                ).start()
            except RuntimeError:
                self._future.cancel()
                self._future = None
                self.failed = True
                self._next_read = self._clock() + self._interval

    def close(self) -> None:
        self._closed = True
        if self._future is not None:
            self._future.cancel()
            self._future = None
