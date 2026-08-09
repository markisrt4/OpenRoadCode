"""Adapt a physical pushbutton into generic input events."""

from input_events import (
    InputDeviceId,
    InputDeviceType,
    InputEvent,
    InputEventType,
    InputHandlerIf,
)
from hardware_io.buttons.push_button_callback_if import PushButtonCallbackIf
from hardware_io.buttons.push_button_if import PushButtonIf


class PushButtonInputAdapter(PushButtonCallbackIf):
    def __init__(
        self,
        button: PushButtonIf,
        device_id: InputDeviceId,
        input_handler: InputHandlerIf,
    ) -> None:
        if device_id.device_type is not InputDeviceType.PUSHBUTTON:
            raise ValueError("PushButtonInputAdapter requires a PUSHBUTTON device ID")
        self._button = button
        self._device_id = device_id
        self._input_handler = input_handler

    def connect(self) -> None:
        self._button.set_callback(self)
        self._button.start()

    def disconnect(self) -> None:
        try:
            self._button.stop()
        finally:
            self._button.set_callback(None)

    def pressed(self) -> None:
        self._publish(InputEventType.BUTTON_PRESSED)

    def released(self) -> None:
        self._publish(InputEventType.BUTTON_RELEASED)

    def _publish(self, event_type: InputEventType) -> None:
        self._input_handler.handle_input_event(
            InputEvent(self._device_id, event_type)
        )
