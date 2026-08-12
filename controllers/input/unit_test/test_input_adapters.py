# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

import unittest

from input_events import InputDeviceId, InputDeviceType, InputEventType
from controllers.input.keyboard_input_adapter import KeyboardInputAdapter
from hardware_io.keyboard import KeyboardReaderIf
from controllers.input.push_button_input_adapter import PushButtonInputAdapter


class RecordingHandler:
    def __init__(self) -> None:
        self.events = []

    def handle_input_event(self, event) -> None:
        self.events.append(event)


class FakeKeyboard:
    is_running = False

    def start(self, callback) -> None:
        self.callback = callback

    def stop(self) -> None:
        pass


class FakeButton:
    def set_callback(self, callback) -> None:
        self.callback = callback

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass


class InputAdapterTest(unittest.TestCase):
    def test_keyboard_adapter_is_typed_against_reader_contract(self) -> None:
        self.assertTrue(
            {"open", "close", "read_keys", "start", "stop"}
            <= KeyboardReaderIf.__abstractmethods__
        )

    def test_keyboard_publishes_generic_button_press(self) -> None:
        handler = RecordingHandler()
        keyboard = FakeKeyboard()
        adapter = KeyboardInputAdapter(
            keyboard, InputDeviceId(InputDeviceType.KEYBOARD), handler
        )
        adapter.connect()
        keyboard.callback("KEY_HOME")

        self.assertEqual(handler.events[0].event_type, InputEventType.BUTTON_PRESSED)
        self.assertEqual(handler.events[0].value, "KEY_HOME")

    def test_pushbutton_publishes_press_and_release(self) -> None:
        handler = RecordingHandler()
        button = FakeButton()
        adapter = PushButtonInputAdapter(
            button, InputDeviceId(InputDeviceType.PUSHBUTTON, 2), handler
        )
        adapter.connect()
        button.callback.pressed()
        button.callback.released()

        self.assertEqual(
            [event.event_type for event in handler.events],
            [InputEventType.BUTTON_PRESSED, InputEventType.BUTTON_RELEASED],
        )


if __name__ == "__main__":
    unittest.main()
