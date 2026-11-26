# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Frontend-thread callback scheduling and cancellation."""

import tkinter as tk
from collections.abc import Callable

from frontends.common.ui_callback_queue import UiCallbackQueue


class UiCallbackMixin:
    """Share the shell callback lifecycle without owning the root window."""

    _root: tk.Tk
    _closing: bool
    _callback_queue: UiCallbackQueue
    _ui_callbacks: set[str]

    def dispatch_ui(self, callback: Callable[[], None]) -> None:
        """Queue work from any thread without calling Tk; discard it after shutdown."""
        self._callback_queue.dispatch_ui(callback)

    def _drain_ui_callbacks(self) -> None:
        try:
            self._callback_queue.dispatch_pending()
        finally:
            if not self._closing:
                self.schedule_ui_callback(16, self._drain_ui_callbacks)

    def schedule_ui_callback(self, delay_ms: int, callback: Callable[[], None]) -> object:
        """Schedule a timer from the frontend thread only; closed timers are inert."""
        if self._closing:
            return None

        token: str | None = None
        invoked = False

        def invoke() -> None:
            nonlocal invoked
            invoked = True
            if token is not None:
                self._ui_callbacks.discard(token)
            if not self._closing:
                callback()

        token = self._root.after(delay_ms, invoke)
        if not invoked:
            self._ui_callbacks.add(token)
        return token

    def cancel_ui_callback(self, callback_id: object) -> None:
        """Cancel a timer on the frontend thread, tolerating destroyed Tk resources."""
        if not isinstance(callback_id, str):
            return
        self._ui_callbacks.discard(callback_id)
        try:
            self._root.after_cancel(callback_id)
        except tk.TclError:
            pass
