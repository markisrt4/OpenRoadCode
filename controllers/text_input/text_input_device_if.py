"""Interface for user text-input devices."""

from abc import ABC, abstractmethod
from collections.abc import Callable

from .text_input_request import TextInputRequest


TextSubmittedCallback = Callable[[str], None]
TextCancelledCallback = Callable[[], None]


class TextInputDeviceIf(ABC):
    """Contract for a device that can satisfy a text-input request."""

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Return whether this text-input device is available for use."""
        ...

    @property
    @abstractmethod
    def is_active(self) -> bool:
        """Return whether this device currently owns an active request."""
        ...

    @abstractmethod
    def request_text(
        self,
        request: TextInputRequest,
        on_submit: TextSubmittedCallback,
        on_cancel: TextCancelledCallback | None = None,
    ) -> None:
        """Begin collecting text for the supplied request."""
        ...

    @abstractmethod
    def cancel(self) -> None:
        """Cancel the active request, if one exists."""
        ...
