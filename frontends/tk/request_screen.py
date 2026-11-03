# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""A shell destination which emits an injected semantic presentation request."""
from collections.abc import Callable
from frontends.tk.tk_screen import TkScreen
from ui.screen_ui_if import ScreenId


class RequestScreen(TkScreen):
    def __init__(self, screen_id: str, request: Callable[[], None]):
        super().__init__(ScreenId(screen_id))
        self._request = request

    def show(self):
        self._request()
