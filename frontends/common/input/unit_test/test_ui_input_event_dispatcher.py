# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

import unittest

from input_events import (
    InputDeviceId,
    InputDeviceType,
    InputEvent,
    InputEventType,
    InputHandlerIf,
)
from frontends.common.input import UiInputEventDispatcher


class RecordingHandler(InputHandlerIf):
    def __init__(self) -> None:
        self.events: list[InputEvent] = []

    def handle_input_event(self, event: InputEvent) -> None:
        self.events.append(event)


class UiInputEventDispatcherTest(unittest.TestCase):
    def test_events_wait_until_frontend_dispatches_them(self) -> None:
        target = RecordingHandler()
        dispatcher = UiInputEventDispatcher(target)
        event = InputEvent(
            InputDeviceId(InputDeviceType.ROTARY_ENCODER, 1),
            InputEventType.BUTTON_PRESSED,
        )

        dispatcher.handle_input_event(event)
        self.assertEqual(target.events, [])
        dispatcher.dispatch_pending()

        self.assertEqual(target.events, [event])

    def test_pending_events_can_be_discarded(self) -> None:
        target = RecordingHandler()
        dispatcher = UiInputEventDispatcher(target)
        dispatcher.handle_input_event(
            InputEvent(
                InputDeviceId(InputDeviceType.KEYBOARD),
                InputEventType.BUTTON_PRESSED,
                "KEY_ENTER",
            )
        )

        dispatcher.discard_pending()
        dispatcher.dispatch_pending()

        self.assertEqual(target.events, [])


if __name__ == "__main__":
    unittest.main()
