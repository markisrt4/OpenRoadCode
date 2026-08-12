# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Toolkit-independent UI event-loop dispatch contract."""

from collections.abc import Callable
from typing import Protocol


class UiDispatcherIf(Protocol):
    """Schedule callbacks without exposing a concrete frontend event loop."""

    def dispatch_ui(self, callback: Callable[[], None]) -> None:
        """Arrange for work to run on the frontend thread.

        @param callback Work to invoke on the frontend thread.
        """
        ...

    def schedule_ui_callback(
        self, delay_ms: int, callback: Callable[[], None]
    ) -> object:
        """Run work after a delay and return a cancellation token.

        @param delay_ms Non-negative scheduling delay in milliseconds.
        @param callback Work to invoke after the delay.
        @return Opaque token identifying the pending callback.
        """
        ...

    def cancel_ui_callback(self, callback_id: object) -> None:
        """Cancel a previously scheduled callback when it is still pending.

        @param callback_id Token returned by schedule_ui_callback().
        """
        ...
