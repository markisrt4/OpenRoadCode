"""Hardware contract for provider-independent keyboard key readers."""

from abc import ABC, abstractmethod
from collections.abc import Callable, Iterator


KeyCallback = Callable[[str], None]


class KeyboardReaderIf(ABC):
    """Read normalized key names from a physical keyboard source."""

    @property
    @abstractmethod
    def device_path(self) -> str | None:
        """Return the selected device path, if one has been selected.

        @return Selected device path, or None before device selection.
        """
        ...

    @property
    @abstractmethod
    def device_name(self) -> str | None:
        """Return the connected device name, if available.

        @return Connected device name, or None when unavailable.
        """
        ...

    @property
    @abstractmethod
    def is_running(self) -> bool:
        """Return whether background key monitoring is active.

        @return True while background monitoring is active.
        """
        ...

    @abstractmethod
    def open(self) -> None:
        """Open or select the underlying keyboard source."""
        ...

    @abstractmethod
    def close(self) -> None:
        """Stop monitoring and release the underlying source."""
        ...

    @abstractmethod
    def read_keys(self) -> Iterator[str]:
        """Yield normalized key names from the source until it closes.

        @return Iterator of normalized key names.
        """
        ...

    @abstractmethod
    def start(self, callback: KeyCallback | None = None) -> None:
        """Start background monitoring using the configured callback.

        @param callback Optional consumer invoked for each normalized key.
        """
        ...

    @abstractmethod
    def stop(self) -> None:
        """Stop background monitoring without discarding configuration."""
        ...
