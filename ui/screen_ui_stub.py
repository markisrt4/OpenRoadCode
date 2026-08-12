# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Concrete no-op navigable screen implementation."""

from ui.screen_ui_if import ScreenId, ScreenUiIf
from ui.ui_action import UiAction


class ScreenUiStub(ScreenUiIf):
    """Provide inert lifecycle and action behavior for a named screen."""

    def __init__(self, screen_id: ScreenId = ScreenId("stub")) -> None:
        self._screen_id = screen_id

    @property
    def screen_id(self) -> ScreenId:
        return self._screen_id

    def show(self) -> None:
        pass

    def hide(self) -> None:
        pass

    def handle_ui_action(self, action: UiAction) -> bool:
        return False
