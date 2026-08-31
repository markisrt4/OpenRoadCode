# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Native games launcher panel for orcUi."""

from __future__ import annotations

import shutil
import tkinter as tk
from collections.abc import Callable
from pathlib import Path

from controllers.games.game_catalog import load_game_catalog
from controllers.games.game_launcher import GameLauncher
from controllers.games.game_types import GameDefinition

BG = "#05090d"
PANEL = "#0b1117"
BORDER = "#25313b"
TEXT = "#edf2f5"
MUTED = "#89959e"
GREEN = "#84ce1f"
RED = "#f15a16"
BLUE = "#168bd1"


class GamesPanel(tk.Frame):
    """Touch-friendly launcher for configured native Linux games."""

    def __init__(self, parent: tk.Misc, on_back: Callable[[], None]) -> None:
        super().__init__(parent, bg=BG)
        self._on_back = on_back
        self._launcher = GameLauncher()
        self._status: tk.Label
        self._games = self._load_games()
        self._build()

    @staticmethod
    def _load_games() -> list[GameDefinition]:
        config = Path(__file__).resolve().parents[2] / "config" / "games.toml"
        try:
            return load_game_catalog(config)
        except (OSError, KeyError, TypeError, ValueError):
            return []

    def _build(self) -> None:
        header = tk.Frame(self, bg=BG)
        header.pack(fill=tk.X, pady=(4, 10))
        tk.Button(
            header,
            text="‹ HOME",
            command=self._on_back,
            bg="#101820",
            fg=TEXT,
            relief=tk.FLAT,
            font=("Sans", 11, "bold"),
            padx=14,
            pady=7,
            cursor="hand2",
        ).pack(side=tk.LEFT)
        tk.Label(header, text="GAMES", fg=GREEN, bg=BG, font=("Sans", 22, "bold")).pack(side=tk.LEFT, padx=18)
        self._status = tk.Label(header, text="Choose a game", fg=MUTED, bg=BG, font=("Sans", 10))
        self._status.pack(side=tk.RIGHT, padx=10)

        body = tk.Frame(self, bg=BG)
        body.pack(fill=tk.BOTH, expand=True)
        for column in range(2):
            body.grid_columnconfigure(column, weight=1, uniform="game")
        for row in range(4):
            body.grid_rowconfigure(row, weight=1, uniform="game")

        if not self._games:
            tk.Label(body, text="No game catalog available", fg=MUTED, bg=BG, font=("Sans", 18, "bold")).place(relx=.5, rely=.45, anchor="center")
            return

        for index, game in enumerate(self._games[:8]):
            self._game_card(body, game).grid(
                row=index // 2,
                column=index % 2,
                sticky="nsew",
                padx=6,
                pady=6,
            )

    def _game_card(self, parent: tk.Misc, game: GameDefinition) -> tk.Frame:
        card = tk.Frame(parent, bg=PANEL, highlightthickness=1, highlightbackground=BORDER)
        card.grid_columnconfigure(0, weight=1)
        installed = shutil.which(game.command[0]) is not None
        available = game.enabled and installed
        tk.Label(card, text=game.name, fg=TEXT if available else MUTED, bg=PANEL, font=("Sans", 14, "bold")).grid(row=0, column=0, sticky="w", padx=14, pady=(12, 3))
        tk.Label(card, text=game.description, fg=MUTED, bg=PANEL, font=("Sans", 9), anchor="w").grid(row=1, column=0, sticky="ew", padx=14)
        state = "READY" if available else ("DISABLED" if not game.enabled else "NOT INSTALLED")
        tk.Label(card, text=state, fg=GREEN if available else MUTED, bg=PANEL, font=("Sans", 8, "bold")).grid(row=2, column=0, sticky="w", padx=14, pady=(5, 8))
        tk.Button(
            card,
            text="PLAY" if available else state,
            command=lambda selected=game: self._launch(selected),
            state=tk.NORMAL if available else tk.DISABLED,
            bg="#102018" if available else "#11161a",
            fg=GREEN if available else MUTED,
            activebackground="#183024",
            activeforeground=TEXT,
            disabledforeground=MUTED,
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=GREEN if available else BORDER,
            font=("Sans", 10, "bold"),
            padx=16,
            pady=7,
            cursor="hand2" if available else "arrow",
        ).grid(row=0, column=1, rowspan=3, padx=14, pady=12)
        return card

    def _launch(self, game: GameDefinition) -> None:
        if self._launcher.is_running():
            self._status.configure(text="A game is already running", fg=RED)
            return
        try:
            self._launcher.launch(game)
        except (OSError, RuntimeError, ValueError) as error:
            self._status.configure(text=f"Launch failed: {error}", fg=RED)
            return
        self._status.configure(text=f"Running: {game.name}", fg=BLUE)

    def stop(self) -> None:
        """Stop a game launched from this panel."""
        self._launcher.stop()
