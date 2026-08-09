"""Narrow host contract required by reusable Tk screens."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from typing import Protocol

from ui.screen_ui_if import ScreenUiIf


class TkScreenHostIf(Protocol):
    """Operations a Tk application shell provides to hosted screens."""

    @property
    def screen_parent(self) -> tk.Misc:
        """Return the Tk container in which screen content is created.

        @return Parent Tk widget for hosted screen content.
        """
        ...

    def activate_screen(self, screen: ScreenUiIf) -> None:
        """Make a screen the target for semantic UI actions.

        @param screen Screen that becomes the active action target.
        """
        ...

    def clear_screen_content(self) -> None:
        """Destroy content belonging to the previously displayed screen."""
        ...

    def set_screen_title(self, title: str) -> None:
        """Set the application-shell title for the active screen.

        @param title User-visible title to display in the shell.
        """
        ...

    def set_screen_back_action(self, action: Callable[[], None]) -> None:
        """Configure and show the active screen's back action.

        @param action Callback invoked by the shell back control.
        """
        ...

    def set_screen_status(self, message: str) -> None:
        """Set application status associated with the active screen.

        @param message User-visible status message.
        """
        ...

    def schedule_ui_callback(
        self,
        delay_ms: int,
        callback: Callable[[], None],
    ) -> object:
        """Schedule work on the Tk event-loop thread.

        @param delay_ms Non-negative delay in milliseconds.
        @param callback Work to invoke after the delay.
        @return Opaque token that can cancel the pending callback.
        """
        ...

    def cancel_ui_callback(self, callback_id: object) -> None:
        """Cancel scheduled UI work when it has not yet run.

        @param callback_id Token returned by schedule_ui_callback().
        """
        ...
