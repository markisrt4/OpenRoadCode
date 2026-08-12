# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Queue physical input for delivery by a frontend event loop."""

from queue import Empty, SimpleQueue

from input_events import InputEvent, InputHandlerIf


class UiInputEventDispatcher(InputHandlerIf):
    """Thread-safe queue between hardware adapters and input handling."""

    def __init__(self, target: InputHandlerIf) -> None:
        self._target = target
        self._events: SimpleQueue[InputEvent] = SimpleQueue()

    def handle_input_event(self, event: InputEvent) -> None:
        """Queue an event without invoking UI behavior on the caller's thread."""
        self._events.put(event)

    def dispatch_pending(self) -> None:
        """Deliver all queued events on the calling frontend thread."""
        while True:
            try:
                event = self._events.get_nowait()
            except Empty:
                return
            self._target.handle_input_event(event)

    def discard_pending(self) -> None:
        """Discard events that must not cross a lifecycle transition."""
        while True:
            try:
                self._events.get_nowait()
            except Empty:
                return
