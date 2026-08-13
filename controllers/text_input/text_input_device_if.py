from abc import ABC, abstractmethod
from collections.abc import Callable

from controllers.text_input.text_input_request import TextInputRequest


TextSubmittedCallback = Callable[[str], None]
TextCancelledCallback = Callable[[], None]


class TextInputDeviceIf(ABC):
    """Interface for devices capable of collecting a string from the user."""

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Return whether this text input device is currently available."""
        ...

    @property
    @abstractmethod
    def is_active(self) -> bool:
        """Return whether this device currently has an active request."""
        ...

    @abstractmethod
    def request_text(
        self,
        request: TextInputRequest,
        on_submit: TextSubmittedCallback,
        on_cancel: TextCancelledCallback | None = None,
    ) -> None:
        """Begin collecting text from the user."""
        ...

    @abstractmethod
    def cancel(self) -> None:
        """Cancel the current request, if any."""
        ...
