# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from abc import abstractmethod

from ui.screen_ui_if import ScreenId, ScreenUiIf
from ui.ui_action import UiAction


class TkScreen(ScreenUiIf):
    """Shared Tkinter base for objects that compose navigable screens.

    This is deliberately a Tk-specific implementation base, not a portable
    interface. Individual screens compose panels inside the application's
    content frame.
    """

    def __init__(self, screen_id: ScreenId) -> None:
        self._screen_id = screen_id

    @property
    def screen_id(self) -> ScreenId:
        return self._screen_id

    @abstractmethod
    def show(self) -> None:
        """Build and display this screen's Tk panels."""
        ...

    def hide(self) -> None:
        """Release transient screen activity before navigating away."""

    def handle_ui_action(self, action: UiAction) -> bool:
        """Return False until a screen provides semantic action handling."""
        return False
