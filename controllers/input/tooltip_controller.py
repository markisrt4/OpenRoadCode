# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Delayed tooltip policy with stale completion rejection."""

from ui.tooltip_if import TooltipRequestHandlerIf, TooltipState, TooltipUiIf
from ui.ui_dispatcher_if import UiDispatcherIf


class TooltipController(TooltipRequestHandlerIf):
    """Own a tooltip session; all requests run on the UI dispatch thread."""

    def __init__(self, view: TooltipUiIf, dispatcher: UiDispatcherIf, *, delay_ms: int = 500) -> None:
        if not isinstance(view, TooltipUiIf):
            raise TypeError("Tooltip requires TooltipUiIf")
        if delay_ms < 0:
            raise ValueError("tooltip delay must be nonnegative")
        self._view = view
        self._dispatcher = dispatcher
        self._delay_ms = delay_ms
        self._pending = None
        self._generation = 0
        self._closed = False

    def request_show(self, text: str) -> None:
        if self._closed:
            return
        self.request_hide()
        if not text.strip():
            return
        generation = self._generation

        def show():
            if self._closed or generation != self._generation:
                return
            self._pending = None
            self._view.set_tooltip_state(TooltipState(text=text, visible=True))

        self._pending = self._dispatcher.schedule_ui_callback(self._delay_ms, show)

    def request_hide(self) -> None:
        if self._closed:
            return
        self._generation += 1
        token, self._pending = self._pending, None
        if token is not None:
            self._dispatcher.cancel_ui_callback(token)
        self._view.set_tooltip_state(TooltipState())

    def close(self) -> None:
        if self._closed:
            return
        self.request_hide()
        self._closed = True
