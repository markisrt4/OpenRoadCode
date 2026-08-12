# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Adapt physical rotary encoder events into generic input events."""

from __future__ import annotations

from input_events import (
    InputDeviceId,
    InputDeviceType,
    InputEvent,
    InputEventType,
    InputHandlerIf,
)
from hardware_io.rotary_encoder.rotary_encoder_if import RotaryEncoderIf


class RotaryEncoderInputAdapter:
    """Connect a RotaryEncoderIf to the generic input subsystem."""

    def __init__(
        self,
        encoder: RotaryEncoderIf,
        device_id: InputDeviceId,
        input_handler: InputHandlerIf,
    ) -> None:
        if device_id.device_type is not InputDeviceType.ROTARY_ENCODER:
            raise ValueError(
                "RotaryEncoderInputAdapter requires a "
                "ROTARY_ENCODER device ID"
            )

        self._encoder = encoder
        self._device_id = device_id
        self._input_handler = input_handler

    @property
    def is_connected(self) -> bool:
        """Return whether the physical encoder is being monitored."""

        return self._encoder.is_running

    def connect(self) -> None:
        """Start receiving physical rotary encoder events."""

        self._encoder.start(
            rotated=self._rotated,
            button_pressed=self._button_pressed,
            button_released=self._button_released,
        )

    def disconnect(self) -> None:
        """Stop receiving physical rotary encoder events."""

        self._encoder.stop()

    def poll(self) -> None:
        """
        Perform implementation-specific encoder polling.

        Callback-driven encoders may implement this as a no-op.
        """

        self._encoder.poll()

    def _rotated(self, turns: int) -> None:
        """Forward signed encoder rotation as an InputEvent."""

        if turns == 0:
            return

        self._input_handler.handle_input_event(
            InputEvent(
                device_id=self._device_id,
                event_type=InputEventType.ROTATED,
                value=turns,
            )
        )

    def _button_pressed(self) -> None:
        """Forward a physical encoder-button press."""

        self._input_handler.handle_input_event(
            InputEvent(
                device_id=self._device_id,
                event_type=InputEventType.BUTTON_PRESSED,
            )
        )

    def _button_released(self) -> None:
        """Forward a physical encoder-button release."""

        self._input_handler.handle_input_event(
            InputEvent(
                device_id=self._device_id,
                event_type=InputEventType.BUTTON_RELEASED,
            )
        )
