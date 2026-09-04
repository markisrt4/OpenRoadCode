"""Interface for embedding native application windows into a frontend host."""

from abc import ABC, abstractmethod


class WindowEmbedderIf(ABC):
    """Frontend adapter for hosting an external application window."""

    @staticmethod
    @abstractmethod
    def supported() -> bool:
        """Return whether this embedding backend is available.

        @return ``True`` when the required native embedding support is available.
        """

    @property
    @abstractmethod
    def window_id(self) -> int | None:
        """Return the currently embedded native window identifier.

        @return The embedded native window identifier, or ``None`` when no window is embedded.
        """

    @abstractmethod
    def embed(
        self,
        process_id: int,
        host_window_id: int,
        width: int,
        height: int,
        *,
        window_name: str | None = None,
        window_class: str | None = None,
    ) -> int:
        """Embed a matching application window into the supplied frontend host.

        @param process_id Process identifier of the application whose window should be embedded.
        @param host_window_id Native window identifier of the frontend host.
        @param width Initial embedded-window width in pixels.
        @param height Initial embedded-window height in pixels.
        @param window_name Optional native window-name match used during discovery.
        @param window_class Optional native window-class match used during discovery.
        @return The native identifier of the embedded application window.
        """

    @abstractmethod
    def resize(self, width: int, height: int) -> None:
        """Resize the embedded window to match its host.

        @param width New embedded-window width in pixels.
        @param height New embedded-window height in pixels.
        """

    @abstractmethod
    def clear(self) -> None:
        """Forget the currently embedded window."""
