# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import unittest
from collections.abc import Callable

from apps.carUi.runtime.car_ui_input_runtime import CarUiInputRuntime
from input_events import (
    InputDeviceId,
    InputDeviceType,
    InputEvent,
    InputEventType,
    InputHandlerIf,
)


class FakeDispatcher:
    def __init__(self) -> None:
        self.callbacks: dict[str, Callable[[], None]] = {}
        self._next_id = 0

    def dispatch_ui(self, callback: Callable[[], None]) -> None:
        callback()

    def schedule_ui_callback(self, _delay_ms: int, callback: Callable[[], None]) -> str:
        self._next_id += 1
        after_id = f"after-{self._next_id}"
        self.callbacks[after_id] = callback
        return after_id

    def cancel_ui_callback(self, after_id: object) -> None:
        self.callbacks.pop(after_id, None)

    def run_next(self) -> None:
        after_id = next(iter(self.callbacks))
        callback = self.callbacks.pop(after_id)
        callback()


class FakeEncoder:
    def __init__(self, *, start_error: Exception | None = None) -> None:
        self.is_running = False
        self.start_error = start_error
        self.poll_count = 0
        self.rotated: Callable[[int], None] | None = None
        self.button_pressed: Callable[[], None] | None = None
        self.button_released: Callable[[], None] | None = None

    def start(
        self,
        rotated: Callable[[int], None],
        button_pressed: Callable[[], None] | None = None,
        button_released: Callable[[], None] | None = None,
    ) -> None:
        if self.start_error is not None:
            raise self.start_error
        self.is_running = True
        self.rotated = rotated
        self.button_pressed = button_pressed
        self.button_released = button_released

    def stop(self) -> None:
        self.is_running = False

    def poll(self) -> None:
        self.poll_count += 1


class RecordingInputHandler(InputHandlerIf):
    def __init__(self) -> None:
        self.events: list[InputEvent] = []

    def handle_input_event(self, event: InputEvent) -> None:
        self.events.append(event)


class CarUiInputRuntimeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.dispatcher = FakeDispatcher()
        self.encoders = [FakeEncoder(), FakeEncoder(), FakeEncoder()]
        self.device_ids = tuple(
            InputDeviceId(InputDeviceType.ROTARY_ENCODER, index)
            for index in range(len(self.encoders))
        )
        self.input_handler = RecordingInputHandler()
        self.router = CarUiInputRuntime(
            dispatcher=self.dispatcher,
            encoders=self.encoders,
            device_ids=self.device_ids,
            input_handler=self.input_handler,
        )

    def tearDown(self) -> None:
        self.router.stop()

    def test_rotation_preserves_device_and_step_count(self) -> None:
        self.router.start()

        self.encoders[1].rotated(2)  # type: ignore[misc]
        self.encoders[2].rotated(-1)  # type: ignore[misc]
        self.dispatcher.run_next()

        self.assertEqual(
            [
                InputEvent(self.device_ids[1], InputEventType.ROTATED, 1),
                InputEvent(self.device_ids[1], InputEventType.ROTATED, 1),
                InputEvent(self.device_ids[2], InputEventType.ROTATED, -1),
            ],
            self.input_handler.events,
        )

    def test_buttons_are_forwarded_as_generic_input(self) -> None:
        self.router.start()

        self.encoders[1].button_pressed()  # type: ignore[misc]
        self.encoders[1].button_released()  # type: ignore[misc]
        self.dispatcher.run_next()

        self.assertEqual(
            [
                InputEvent(self.device_ids[1], InputEventType.BUTTON_PRESSED),
                InputEvent(self.device_ids[1], InputEventType.BUTTON_RELEASED),
            ],
            self.input_handler.events,
        )

    def test_device_id_count_must_match_encoders(self) -> None:
        with self.assertRaisesRegex(ValueError, "device_ids"):
            CarUiInputRuntime(
                dispatcher=self.dispatcher,
                encoders=[FakeEncoder()],
                device_ids=(),
                input_handler=self.input_handler,
            )

    def test_device_ids_must_be_unique(self) -> None:
        with self.assertRaisesRegex(ValueError, "unique"):
            CarUiInputRuntime(
                dispatcher=self.dispatcher,
                encoders=[FakeEncoder(), FakeEncoder()],
                device_ids=(self.device_ids[0], self.device_ids[0]),
                input_handler=self.input_handler,
            )

    def test_unavailable_encoder_does_not_prevent_others_starting(self) -> None:
        encoders = [
            FakeEncoder(),
            FakeEncoder(start_error=ValueError("No I2C device at address: 0x38")),
            FakeEncoder(),
        ]
        router = CarUiInputRuntime(
            dispatcher=self.dispatcher,
            encoders=encoders,
            device_ids=self.device_ids,
            input_handler=self.input_handler,
        )

        try:
            router.start()
            self.dispatcher.run_next()

            self.assertTrue(router.is_running)
            self.assertTrue(encoders[0].is_running)
            self.assertFalse(encoders[1].is_running)
            self.assertTrue(encoders[2].is_running)
            self.assertEqual(1, encoders[0].poll_count)
            self.assertEqual(0, encoders[1].poll_count)
            self.assertEqual(1, encoders[2].poll_count)
        finally:
            router.stop()


if __name__ == "__main__":
    unittest.main()
