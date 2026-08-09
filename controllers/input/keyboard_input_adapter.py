"""Adapt physical keyboard events into generic input events."""

from __future__ import annotations

from input_events import (
    InputDeviceId,
    InputDeviceType,
    InputEvent,
    InputEventType,
    InputHandlerIf,
)
from hardware_io.keyboard import KeyboardReaderIf


class KeyboardInputAdapter:
    """Connect a KeyboardReader to the generic input subsystem."""

    def __init__(
        self,
        keyboard: KeyboardReaderIf,
        device_id: InputDeviceId,
        input_handler: InputHandlerIf,
    ) -> None:
        if device_id.device_type is not InputDeviceType.KEYBOARD:
            raise ValueError(
                "KeyboardInputAdapter requires a KEYBOARD device ID"
            )

        self._keyboard = keyboard
        self._device_id = device_id
        self._input_handler = input_handler

    @property
    def is_connected(self) -> bool:
        """Return whether the physical keyboard reader is running."""

        return self._keyboard.is_running

    def connect(self) -> None:
        """Start receiving physical keyboard events."""

        self._keyboard.start(self._key_pressed)

    def disconnect(self) -> None:
        """Stop receiving physical keyboard events."""

        self._keyboard.stop()

    def _key_pressed(self, key: str) -> None:
        """Forward one physical key press as an InputEvent."""

        self._input_handler.handle_input_event(
            InputEvent(
                device_id=self._device_id,
                event_type=InputEventType.BUTTON_PRESSED,
                value=key,
            )
        )
