"""Narrow platform adapter contract used by the game runtime controller."""

from typing import Protocol


class GameWindowEmbedderIf(Protocol):
    """Embed and resize one external process window; no toolkit dependencies."""

    def supported(self) -> bool:
        """! @brief Report platform embedding availability.

        @return Whether native embedding is supported.
        """
        ...

    def embed(
        self, process_id: int, host_window_id: int, width: int, height: int, *,
        window_name: str | None = None, window_class: str | None = None,
        relax_size_hints: bool = False,
    ) -> int:
        """! @brief Embed a process window in the supplied native host.

        @param process_id Launched process identifier.
        @param host_window_id Native presentation host handle.
        @param width Host width in pixels.
        @param height Host height in pixels.
        @param window_name Optional window name selector.
        @param window_class Optional window class selector.
        @param relax_size_hints Whether restrictive size hints may be removed.
        @return Embedded window handle.
        """
        ...

    def resize(self, width: int, height: int) -> None:
        """! @brief Resize the embedded window.

        @param width Host width in pixels.
        @param height Host height in pixels.
        """
        ...

    def clear(self) -> None:
        """! @brief Forget native window ownership."""
        ...
