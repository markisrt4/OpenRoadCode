"""Toolkit-neutral lifecycle and native-host contracts for a Games destination."""

from collections.abc import Callable
from typing import Protocol

from .games_ui_if import GamesUiIf


class GamesRuntimeUiIf(Protocol):
    """Render the native host; process and platform operations remain external."""

    def show_runtime_host(self, on_resize: Callable[[int, int], None]) -> tuple[int, int, int]:
        """! @brief Create a native host and return its handle and pixel dimensions.

        @param on_resize Callback receiving the new pixel width and height.
        @return Native host handle, width, and height.
        """
        ...

    def set_runtime_loading(self, loading: bool) -> None:
        """! @brief Show or clear the launch indicator.

        @param loading Whether the launch indicator should be visible.
        """
        ...

    def hide_runtime_host(self) -> None:
        """! @brief Restore the game inventory presentation."""
        ...


class GamesSessionIf(Protocol):
    """Lifecycle consumed by the screen; composition owns its implementation."""

    def activate(self, games_ui: GamesUiIf, runtime_ui: GamesRuntimeUiIf) -> None:
        """! @brief Bind a visible destination and start its inventory.

        @param games_ui Inventory presentation to bind.
        @param runtime_ui Native host presentation to bind.
        """
        ...

    def deactivate(self) -> None:
        """! @brief Unbind presentation and invalidate pending runtime work."""
        ...

    def resize(self, width: int, height: int) -> None:
        """! @brief Request a native host resize without blocking presentation.

        @param width Host width in pixels.
        @param height Host height in pixels.
        """
        ...

    def close(self) -> None:
        """! @brief Retire the session and release its native resources."""
        ...
