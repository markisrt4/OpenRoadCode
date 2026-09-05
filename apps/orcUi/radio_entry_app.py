# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""orcUi application variant with the radio source chooser enabled."""

from __future__ import annotations

import tkinter as tk

from apps.orcUi.main import OrcUiApp
from apps.orcUi.radio_entry_panel import RadioEntryPanel


class RadioEntryOrcUiApp(OrcUiApp):
    """Use the RF/streaming chooser when the RADIO navigation item is opened."""

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
