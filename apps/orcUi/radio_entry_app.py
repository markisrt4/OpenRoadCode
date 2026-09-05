# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Integrated orcUi application with radio source chooser and games support."""

from __future__ import annotations

import tkinter as tk

from apps.launchers.sdrpp_launcher import sync_sdrpp_theme
from apps.orcUi.games_app import GamesOrcUiApp
from apps.orcUi.orc_theme import ThemeMode
from apps.orcUi.radio_entry_panel import RadioEntryPanel


class RadioEntryOrcUiApp(GamesOrcUiApp):
    """Run the integrated cockpit shell with radio and native games support."""

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
        )
        self._radio_panel.pack(fill=tk.BOTH, expand=True)


def main() -> None:
    RadioEntryOrcUiApp().run()
