# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Exercise game text allocation and paging with real Tk geometry."""

import tkinter as tk
import unittest
from pathlib import Path

from controllers.games.game_catalog import load_game_catalog
from frontends.tk.games.games_panel import GamesPanel
from ui.games import GameStatus, GameUiState
from ui.theme import load_theme_bundle


class GamesPanelLayoutTest(unittest.TestCase):
    def setUp(self) -> None:
        try:
            self.root = tk.Tk()
        except tk.TclError as error:
            self.skipTest(f"Tk display unavailable: {error}")
        self.addCleanup(self.root.destroy)
        self.root.tk.call("tk", "scaling", 1.3)
        project = Path(__file__).resolve().parents[4]
        theme = load_theme_bundle(project / "resources/themes/orc-dark.css")
        self.panel = GamesPanel(self.root, theme=theme)
        self.panel.pack(fill=tk.BOTH, expand=True)
        self.games = tuple(
            GameUiState(game_id=game.name, name=game.name, description=game.description,
                        category=game.category, icon=None, status=GameStatus.UNAVAILABLE)
            for game in load_game_catalog(project / "config/games.toml")
        )
        self.panel.set_games(self.games)

    def _check_text_fits(self) -> None:
        self.root.update()
        self.assertTrue(self.panel._next_button.winfo_ismapped())
        for card in self.panel._cards.winfo_children():
            self.assertLessEqual(card.winfo_y() + card.winfo_height(),
                                 self.panel._cards.winfo_height())
            for widget in card.winfo_children():
                if isinstance(widget, (tk.Label, tk.Button)):
                    self.assertGreaterEqual(widget.winfo_height(), widget.winfo_reqheight())
                    self.assertGreaterEqual(widget.winfo_width(), widget.winfo_reqwidth())
                    self.assertLessEqual(widget.winfo_x() + widget.winfo_width(), card.winfo_width())
                    self.assertLessEqual(widget.winfo_y() + widget.winfo_height(), card.winfo_height())

    def test_narrow_and_wide_windows_keep_text_and_pager_visible(self) -> None:
        for size in ("480x340", "900x400", "1200x800"):
            with self.subTest(size=size):
                self.root.geometry(size)
                self.panel._set_filter("puzzle")
                self._check_text_fits()
                seen = set()
                while True:
                    first = self.panel._page * self.panel._page_size
                    seen.update(game.game_id for game in self.panel._visible_games()[
                        first:first + self.panel._page_size])
                    if self.panel._next_button.cget("state") == tk.DISABLED:
                        break
                    self.panel._change_page(1)
                    self._check_text_fits()
                self.assertEqual({game.game_id for game in self.games if game.category == "puzzle"}, seen)

    def test_short_window_keeps_six_games_on_each_full_page(self) -> None:
        self.root.geometry("900x340")
        self.root.update()
        self.assertEqual(6, self.panel._page_size)
        self.assertEqual(6, len(self.panel._cards.winfo_children()))
        self._check_text_fits()
        self.assertEqual("1 / 3", self.panel._page_label.cget("text"))

    def test_runtime_resize_and_return_restore_catalog(self) -> None:
        self.root.geometry("900x400")
        self.root.update()
        self.panel.show_runtime_host(lambda width, height: None)
        self.root.geometry("480x340")
        self.root.update()
        self.panel.hide_runtime_host()
        self._check_text_fits()

    def test_large_fonts_and_install_status_fit(self) -> None:
        self.root.tk.call("tk", "scaling", 2.0)
        self.root.geometry("600x420")
        self.panel.set_games_status("Installing: GNOME Sudoku (Debian)…")
        self.panel._set_filter("puzzle")
        self._check_text_fits()
        self.assertGreaterEqual(self.panel._status.winfo_height(),
                                self.panel._status.winfo_reqheight())
        for button in self.panel._filter_buttons.values():
            self.assertLessEqual(button.winfo_x() + button.winfo_width(),
                                 self.panel._filters.winfo_width())
