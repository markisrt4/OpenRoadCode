# SPDX-License-Identifier: MIT
"""Dashboard calendar lifecycle using an injected panel factory."""

from collections.abc import Callable
import tkinter as tk

from frontends.tk.tk_screen import TkScreen
from ui.screen_ui_if import ScreenId


class DashboardCalendarScreen(TkScreen):
    """Mount a calendar panel only while its destination is active."""

    def __init__(self, app, panel_factory: Callable[[tk.Misc], tk.Widget]):
        super().__init__(ScreenId("calendar"))
        self._app = app
        self._panel_factory = panel_factory
        self._panel = None

    def show(self):
        self.hide()
        self._app.activate_screen(self)
        self._app.clear_screen_content()
        self._app.set_screen_title("CALENDAR")
        self._panel = self._panel_factory(self._app.screen_parent)
        self._panel.pack(fill="both", expand=True)

    def hide(self):
        panel, self._panel = self._panel, None
        if panel is not None and panel.winfo_exists():
            panel.destroy()

    def set_theme_mode(self, mode):
        del mode
        if self._panel is not None:
            self.show()
