from __future__ import annotations

from controllers.radio.radio_controller_if import RadioControllerIf
from controllers.radio.radio_input_adapter_if import RadioInputAdapterIf
from hardware_io.keyboard import KeyboardReader


class KeyboardRadioAdapter(RadioInputAdapterIf):
    """Map normalized keyboard events to radio controller operations."""

    def __init__(
        self,
        keyboard: KeyboardReader,
        radio: RadioControllerIf,
    ) -> None:
        self._keyboard = keyboard
        self._radio = radio

    def connect(self) -> None:
        self._keyboard.start(self._key_pressed)

    def disconnect(self) -> None:
        self._keyboard.stop()

    def _key_pressed(self, key: str) -> None:
        normalized_key = key.strip().upper()
        actions = {
            "KEY_RIGHT": self._radio.frequency_up,
            "KEY_UP": self._radio.frequency_up,
            "KEY_LEFT": self._radio.frequency_down,
            "KEY_DOWN": self._radio.frequency_down,
            "KEY_N": self._radio.next_preset,
            "KEY_PAGEDOWN": self._radio.next_preset,
            "KEY_P": self._radio.previous_preset,
            "KEY_PAGEUP": self._radio.previous_preset,
            "KEY_SPACE": self._radio.start,
        }

        action = actions.get(normalized_key)
        if action is not None:
            action()
