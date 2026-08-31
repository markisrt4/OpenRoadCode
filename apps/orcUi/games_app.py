# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""orcUi application variant with native games integration."""

from __future__ import annotations

import tkinter as tk

from apps.orcUi.games_panel import GamesPanel
from apps.orcUi.main import GREEN, OrcUiApp
from apps.orcUi.orc_theme import ThemeMode, apply_tk_theme


class GamesOrcUiApp(OrcUiApp):
    """Extend the cockpit shell with the native games launcher."""

    def __init__(self) -> None:
        self._games_panel: GamesPanel | None = None
        super().__init__()

    def _build_side_nav(self) -> None:
        nav = tk.Frame(self._root, bg="#070c11", width=112)
        nav.grid(row=1, column=0, sticky="ns", padx=(8, 0), pady=6)
        nav.grid_propagate(False)
        for item in [
            "HOME",
            "NAVIGATION",
            "RADIO",
            "VEHICLE",
            "LIGHTING",
            "GAMES",
            "CONTROLS",
            "SETTINGS",
        ]:
            button = tk.Button(
                nav,
                text=item,
                command=lambda name=item: self._select_nav(name),
                bg="#070c11",
                fg="#c7cdd2",
                activebackground="#101820",
                activeforeground=GREEN,
                relief=tk.FLAT,
                bd=0,
                font=("Sans", 9),
                height=2,
                cursor="hand2",
            )
            button.pack(fill=tk.X, padx=4, pady=1)
            self._nav_buttons[item] = button
        self._paint_nav()

    def _select_nav(self, name: str) -> None:
        if name == "GAMES":
            self._show_games_panel()
            return
        super()._select_nav(name)

    def _clear_content(self) -> None:
        if self._games_panel is not None:
            self._games_panel.stop()
            self._games_panel = None
        super()._clear_content()

    def _show_games_panel(self) -> None:
        self._clear_content()
        self._active_nav = "GAMES"
        self._paint_nav()
        self._games_panel = GamesPanel(self._content, on_back=self._show_home)
        self._games_panel.pack(fill=tk.BOTH, expand=True)
        if self._theme_mode is ThemeMode.LIGHT:
            apply_tk_theme(self._games_panel, self._theme_mode)

    def _shutdown(self) -> None:
        if self._games_panel is not None:
            self._games_panel.stop()
        super()._shutdown()


def main() -> None:
    """Launch orcUi with native games support."""
    GamesOrcUiApp().run()
