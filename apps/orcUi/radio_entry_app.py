# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Integrated orcUi application with radio source chooser and games support."""

from __future__ import annotations

import tkinter as tk

from apps.launchers.sdrpp_launcher import sync_sdrpp_theme
from apps.orcUi.orc_theme import ThemeMode
from apps.orcUi.orc_ui_app import OrcUiApp
from apps.orcUi.radio_entry_panel import RadioEntryPanel
from apps.orcUi.theme_runtime import theme_bundle
from frontends.tk.games import GamesScreen


class RadioEntryOrcUiApp(OrcUiApp):
    """Run the integrated cockpit shell with radio chooser composition."""

    def __init__(self) -> None:
        super().__init__()
        self.register_screen(
            "GAMES",
            GamesScreen(self, theme_mode=lambda: self.theme_mode),
        )

    def _show_radio_panel(self) -> None:
        self._clear_content()
        self._active_nav = "RADIO"
        self._paint_nav()

        sync_sdrpp_theme(
            "Light" if self._theme_mode is ThemeMode.LIGHT else "Dark"
        )

        self._radio_panel = RadioEntryPanel(
            self._content,
            embedder=self._radio_embedder,
            theme=theme_bundle(self._theme_mode),
        )
        self._radio_panel.pack(fill=tk.BOTH, expand=True)


def main() -> None:
    RadioEntryOrcUiApp().run()
