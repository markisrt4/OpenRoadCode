# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT

"""Thread-safe callback submission with frontend-thread delivery and shutdown."""

from collections.abc import Callable
from queue import Empty, SimpleQueue


class UiCallbackQueue:
    """Workers submit; only the frontend thread drains or closes this queue."""

    def __init__(self) -> None:
        self._pending: SimpleQueue[Callable[[], None]] | None = SimpleQueue()

    def dispatch_ui(self, callback: Callable[[], None]) -> None:
        """Enqueue work from any thread; discard submissions after close."""
        pending = self._pending
        if pending is not None:
            pending.put(callback)

    def dispatch_pending(self, limit: int = 100) -> None:
        """Deliver a bounded batch on the frontend thread without starving timers."""
        for _ in range(limit):
            pending = self._pending
            if pending is None:
                return
            try:
                callback = pending.get_nowait()
            except Empty:
                return
            callback()

    def close(self) -> None:
        """Retire the queue so even racing producers cannot deliver late work."""
        self._pending = None
