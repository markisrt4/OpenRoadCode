"""Interface for embedding native application windows into a frontend host."""

from abc import ABC, abstractmethod


class WindowEmbedderIf(ABC):
    """Frontend adapter for hosting an external application window."""

    @staticmethod
    @abstractmethod
    def supported() -> bool:
        """Return whether this embedding backend is available."""

    @property
    @abstractmethod
    def window_id(self) -> int | None:
        """Return the currently embedded native window identifier."""

    @abstractmethod
    def embed(self, process_id: int, host_window_id: int, width: int, height: int) -> int:
        """Embed a process window into the supplied frontend host."""

    @abstractmethod
    def resize(self, width: int, height: int) -> None:
        """Resize the embedded window to match its host."""

    @abstractmethod
    def clear(self) -> None:
        """Forget the currently embedded window."""
