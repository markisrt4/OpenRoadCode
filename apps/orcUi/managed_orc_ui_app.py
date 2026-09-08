# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Runtime-composed ORC shell with a shared Google Earth application."""

from __future__ import annotations

import tkinter as tk

from apps.launchers.google_earth_launcher import GoogleEarthLauncher
from apps.orcUi.navigation_panel import NavigationPanel
from apps.orcUi.orc_ui_app import OrcUiApp


class ManagedOrcUiApp(OrcUiApp):
    """Bind runtime-owned external applications to the integrated shell."""

    def __init__(self, *, earth_launcher: GoogleEarthLauncher) -> None:
        self._earth_launcher = earth_launcher
        super().__init__()

    def _show_navigation_panel(self) -> None:
        self._clear_content()
        self._active_nav = "NAVIGATION"
        self._paint_nav()
        self._navigation_panel = NavigationPanel(
            self._content,
            on_back=self._show_home,
            theme_bundle=self._theme,
            earth_launcher=self._earth_launcher,
        )
        self._navigation_panel.pack(fill=tk.BOTH, expand=True)
        self._root.update_idletasks()
        self._start_map_renderer(self._navigation_panel.map_host_window_id)
