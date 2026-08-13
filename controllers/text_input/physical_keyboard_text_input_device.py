from hardware_io.keyboard import KeyboardReaderIf

from controllers.text_input.text_input_device_if import (
    TextCancelledCallback,
    TextInputDeviceIf,
    TextSubmittedCallback,
)
from controllers.text_input.text_input_request import TextInputRequest


class PhysicalKeyboardTextInputDevice(TextInputDeviceIf):

    def __init__(self, keyboard: KeyboardReaderIf) -> None:
        self._keyboard = keyboard
        self._request: TextInputRequest | None = None
        self._on_submit: TextSubmittedCallback | None = None
        self._on_cancel: TextCancelledCallback | None = None
        self._buffer = ""

    @property
    def is_available(self) -> bool:
        return self._keyboard.device_path is not None

    @property
    def is_active(self) -> bool:
        return self._request is not None

    def request_text(
        self,
        request: TextInputRequest,
        on_submit: TextSubmittedCallback,
        on_cancel: TextCancelledCallback | None = None,
    ) -> None:
        if self.is_active:
            raise RuntimeError("Physical keyboard text input already active")

        self._request = request
        self._on_submit = on_submit
        self._on_cancel = on_cancel
        self._buffer = request.initial_text

        if not self._keyboard.is_running:
            self._keyboard.start(self._handle_key)

    def cancel(self) -> None:
        if not self.is_active:
            return

        callback = self._on_cancel
        self._clear()

        if callback:
            callback()

    def _handle_key(self, key: str) -> None:
        if not self.is_active:
            return

        if key in ("ENTER", "KEY_ENTER"):
            self._submit()
            return

        if key in ("ESC", "KEY_ESC"):
            self.cancel()
            return

        if key in ("BACKSPACE", "KEY_BACKSPACE"):
            self._buffer = self._buffer[:-1]
            return

        if len(key) == 1:
            self._buffer += key

    def _submit(self) -> None:
        assert self._request is not None
        assert self._on_submit is not None

        text = self._buffer.strip()

        if not text and not self._request.allow_empty:
            return

        callback = self._on_submit
        self._clear()

        callback(text)

    def _clear(self) -> None:
        self._request = None
        self._on_submit = None
        self._on_cancel = None
        self._buffer = ""
