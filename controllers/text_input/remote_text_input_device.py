"""Text-input device whose completed strings arrive from a remote transport."""

from .text_input_device_if import (
    TextCancelledCallback,
    TextInputDeviceIf,
    TextSubmittedCallback,
)
from .text_input_request import TextInputRequest


class RemoteTextInputDevice(TextInputDeviceIf):
    """Hold a text request until a remote client submits or cancels it."""

    def __init__(self) -> None:
        self._request: TextInputRequest | None = None
        self._on_submit: TextSubmittedCallback | None = None
        self._on_cancel: TextCancelledCallback | None = None

    @property
    def is_available(self) -> bool:
        return True

    @property
    def is_active(self) -> bool:
        return self._request is not None

    @property
    def request(self) -> TextInputRequest | None:
        """Return the active request for presentation by a remote transport."""
        return self._request

    def request_text(
        self,
        request: TextInputRequest,
        on_submit: TextSubmittedCallback,
        on_cancel: TextCancelledCallback | None = None,
    ) -> None:
        if self.is_active:
            raise RuntimeError("A remote text-input request is already active")

        self._request = request
        self._on_submit = on_submit
        self._on_cancel = on_cancel

    def submit(self, text: str) -> None:
        """Complete the active request with text received remotely."""
        if self._request is None or self._on_submit is None:
            raise RuntimeError("No remote text-input request is active")

        text = text.strip()
        if not text and not self._request.allow_empty:
            raise ValueError("Empty text is not allowed")

        callback = self._on_submit
        self._clear()
        callback(text)

    def cancel(self) -> None:
        if not self.is_active:
            return

        callback = self._on_cancel
        self._clear()
        if callback is not None:
            callback()

    def _clear(self) -> None:
        self._request = None
        self._on_submit = None
        self._on_cancel = None
