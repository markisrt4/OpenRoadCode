# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for normalized physical-input values and handler contracts."""

from dataclasses import FrozenInstanceError
import unittest

from input_events import (
    InputDeviceId,
    InputDeviceType,
    InputEvent,
    InputEventType,
    InputHandlerIf,
)
from input_events.input_event import InputEvent as ModuleInputEvent
from input_events.input_handler_if import InputHandlerIf as ModuleInputHandlerIf


class RecordingInputHandler(InputHandlerIf):
    """Record events to verify the abstract consumer contract."""

    def __init__(self) -> None:
        self.events: list[InputEvent] = []

    def handle_input_event(self, event: InputEvent) -> None:
        self.events.append(event)


class InputEventsTest(unittest.TestCase):
    """Verify the public input-events package behavior."""

    def test_package_exports_canonical_classes(self) -> None:
        self.assertIs(InputEvent, ModuleInputEvent)
        self.assertIs(InputHandlerIf, ModuleInputHandlerIf)

    def test_device_id_defaults_to_first_instance(self) -> None:
        device_id = InputDeviceId(InputDeviceType.KEYBOARD)

        self.assertEqual(device_id.device_type, InputDeviceType.KEYBOARD)
        self.assertEqual(device_id.instance, 0)

    def test_device_ids_are_hashable_and_distinguish_instances(self) -> None:
        first = InputDeviceId(InputDeviceType.ROTARY_ENCODER, 0)
        second = InputDeviceId(InputDeviceType.ROTARY_ENCODER, 1)

        self.assertNotEqual(first, second)
        self.assertEqual({first, second}, {first, second})

    def test_device_id_is_immutable(self) -> None:
        device_id = InputDeviceId(InputDeviceType.PUSHBUTTON, 2)

        with self.assertRaises(FrozenInstanceError):
            device_id.instance = 3  # type: ignore[misc]

    def test_input_event_defaults_to_no_payload(self) -> None:
        event = InputEvent(
            InputDeviceId(InputDeviceType.PUSHBUTTON),
            InputEventType.BUTTON_PRESSED,
        )

        self.assertIsNone(event.value)

    def test_input_event_preserves_event_payload(self) -> None:
        event = InputEvent(
            InputDeviceId(InputDeviceType.ROTARY_ENCODER, 1),
            InputEventType.ROTATED,
            -2,
        )

        self.assertEqual(event.value, -2)

    def test_event_categories_cover_supported_physical_activity(self) -> None:
        self.assertEqual(
            set(InputEventType),
            {
                InputEventType.BUTTON_PRESSED,
                InputEventType.BUTTON_RELEASED,
                InputEventType.ROTATED,
                InputEventType.POINTER_MOVED,
                InputEventType.TOUCH_DOWN,
                InputEventType.TOUCH_UP,
                InputEventType.TOUCH_MOVE,
            },
        )

    def test_input_handler_contract_is_abstract(self) -> None:
        with self.assertRaises(TypeError):
            InputHandlerIf()

    def test_concrete_handler_receives_same_event(self) -> None:
        handler = RecordingInputHandler()
        event = InputEvent(
            InputDeviceId(InputDeviceType.MOUSE),
            InputEventType.POINTER_MOVED,
            (12, 24),
        )

        handler.handle_input_event(event)

        self.assertEqual(handler.events, [event])


if __name__ == "__main__":
    unittest.main()
