"""Shared Tk window-mode configuration."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol


class TkWindow(Protocol):
    """Subset of Tk window methods used to configure fullscreen mode."""

    def after_idle(self, callback: Callable[[], None]) -> object:
        """Schedule a callback after the window enters the event loop."""

    def attributes(self, option: str, value: object) -> object:
        """Set a window-manager attribute."""

    def geometry(self, geometry: str) -> object:
        """Set the window geometry."""

    def update_idletasks(self) -> None:
        """Process pending geometry work."""

    def winfo_screenheight(self) -> int:
        """Return the display height."""

    def winfo_screenwidth(self) -> int:
        """Return the display width."""


def apply_fullscreen(window: TkWindow) -> None:
    """Fill the display and assert Tk fullscreen after the window is mapped.

    Some lightweight X11 window managers ignore a fullscreen request made
    before a Tk window enters its event loop. Explicit geometry provides an
    immediate fallback, and the idle callback repeats the window-manager
    request once the window can receive it.
    """

    def assert_fullscreen() -> None:
        width = window.winfo_screenwidth()
        height = window.winfo_screenheight()
        window.geometry(f"{width}x{height}+0+0")
        window.attributes("-fullscreen", True)

    window.update_idletasks()
    assert_fullscreen()
    window.after_idle(assert_fullscreen)
