# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Toolkit-independent UI event-loop dispatch contract."""

from collections.abc import Callable
from typing import Protocol


class UiDispatcherIf(Protocol):
    """Schedule callbacks without exposing a concrete frontend event loop."""

    def dispatch_ui(self, callback: Callable[[], None]) -> None:
        """Enqueue work from any thread without calling frontend toolkit functions.

        Closed dispatchers discard submissions; callbacks already running finish.

        @param callback Work to invoke on the frontend thread.
        """
        ...

    def schedule_ui_callback(
        self, delay_ms: int, callback: Callable[[], None]
    ) -> object:
        """Schedule a timer on the frontend thread and return a cancellation token.

        Call this from the frontend thread only. Worker completions use
        dispatch_ui(). Closed dispatchers return an inert token.

        @param delay_ms Non-negative scheduling delay in milliseconds.
        @param callback Work to invoke after the delay.
        @return Opaque token identifying the pending callback.
        """
        ...

    def cancel_ui_callback(self, callback_id: object) -> None:
        """Cancel pending work from the frontend thread; inert tokens are harmless.

        @param callback_id Token returned by schedule_ui_callback().
        """
        ...
