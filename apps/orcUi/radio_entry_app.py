# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Integrated orcUi application with radio source chooser and games support."""

from __future__ import annotations

import tkinter as tk

from apps.orcUi.games_app import GamesOrcUiApp
from apps.orcUi.radio_entry_panel import RadioEntryPanel


class RadioEntryOrcUiApp(GamesOrcUiApp):
    """Run the integrated cockpit shell with radio and native games support."""

    def _show_radio_panel(self) -> None:
        self._clear_content()
        self._active_nav = "RADIO"
        self._paint_nav()
        self._radio_panel = RadioEntryPanel(
            self._content,
            embedder=self._radio_embedder,
        )
        self._radio_panel.pack(fill=tk.BOTH, expand=True)


def main() -> None:
    RadioEntryOrcUiApp().run()
