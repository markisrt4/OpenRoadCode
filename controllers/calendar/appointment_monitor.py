# SPDX-License-Identifier: MIT
"""Single-flight cache reader shared by Home calendar consumers."""

from concurrent.futures import Future
from threading import Thread
from time import monotonic


def read_snapshot(future, load):
    if not future.set_running_or_notify_cancel():
        return
    try:
        future.set_result(load())
    except Exception as error:
        future.set_exception(error)


class AppointmentMonitor:
    """Poll from the UI thread; only the loader runs on a worker."""

    def __init__(self, load, *, interval=30, clock=monotonic):
        self._load = load
        self._interval = interval
        self._clock = clock
        self._future = None
        self._next_read = 0
        self.snapshot = None
        self.failed = False

    def poll(self):
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
            Thread(
                target=read_snapshot,
                args=(self._future, self._load),
                daemon=True,
                name="upcoming-calendar-read",
            ).start()

    def close(self):
        if self._future is not None:
            self._future.cancel()
            self._future = None
