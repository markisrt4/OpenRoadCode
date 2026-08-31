# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Native games launcher and installer panel for orcUi."""

from __future__ import annotations

import shutil
import threading
import tkinter as tk
from collections.abc import Callable
from pathlib import Path

from controllers.games.game_catalog import load_game_catalog
from controllers.games.game_launcher import GameLauncher
from controllers.games.game_types import GameDefinition
from controllers.games.termux_game_installer import TermuxGameInstaller

BG = "#05090d"
PANEL = "#0b1117"
BORDER = "#25313b"
TEXT = "#edf2f5"
MUTED = "#89959e"
GREEN = "#84ce1f"
RED = "#f15a16"
BLUE = "#168bd1"


class GamesPanel(tk.Frame):
    """Touch-friendly launcher and installer for configured native games."""

    def __init__(self, parent: tk.Misc, on_back: Callable[[], None]) -> None:
        super().__init__(parent, bg=BG)
        self._on_back = on_back
        self._launcher = GameLauncher()
        self._installer = TermuxGameInstaller()
        self._status: tk.Label
        self._body: tk.Frame
        self._installing = False
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

        self._body = tk.Frame(self, bg=BG)
        self._body.pack(fill=tk.BOTH, expand=True)
        for column in range(2):
            self._body.grid_columnconfigure(column, weight=1, uniform="game")
        for row in range(4):
            self._body.grid_rowconfigure(row, weight=1, uniform="game")
        self._refresh_cards()

    def _refresh_cards(self) -> None:
        for child in self._body.winfo_children():
            child.destroy()

        if not self._games:
            tk.Label(self._body, text="No game catalog available", fg=MUTED, bg=BG, font=("Sans", 18, "bold")).place(relx=.5, rely=.45, anchor="center")
            return

        for index, game in enumerate(self._games[:8]):
            self._game_card(self._body, game).grid(
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
        installable = False
        if game.enabled and not installed and not self._installing:
            try:
                installable = self._installer.is_available(game)
            except OSError:
                installable = False

        if not game.enabled:
            state = "DISABLED"
            action = state
            command = None
        elif installed:
            state = "READY"
            action = "PLAY"
            command = lambda selected=game: self._launch(selected)
        elif installable:
            state = "AVAILABLE"
            action = "INSTALL"
            command = lambda selected=game: self._install(selected)
        else:
            state = "UNAVAILABLE"
            action = state
            command = None

        actionable = command is not None and not self._installing
        accent = GREEN if installed else (BLUE if installable else MUTED)
        tk.Label(card, text=game.name, fg=TEXT if actionable or installed else MUTED, bg=PANEL, font=("Sans", 14, "bold")).grid(row=0, column=0, sticky="w", padx=14, pady=(12, 3))
        tk.Label(card, text=game.description, fg=MUTED, bg=PANEL, font=("Sans", 9), anchor="w").grid(row=1, column=0, sticky="ew", padx=14)
        tk.Label(card, text=state, fg=accent, bg=PANEL, font=("Sans", 8, "bold")).grid(row=2, column=0, sticky="w", padx=14, pady=(5, 8))
        tk.Button(
            card,
            text=action,
            command=command,
            state=tk.NORMAL if actionable else tk.DISABLED,
            bg="#102018" if installed else ("#0d1b24" if installable else "#11161a"),
            fg=accent,
            activebackground="#183024",
            activeforeground=TEXT,
            disabledforeground=MUTED,
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=accent if actionable else BORDER,
            font=("Sans", 10, "bold"),
            padx=16,
            pady=7,
            cursor="hand2" if actionable else "arrow",
        ).grid(row=0, column=1, rowspan=3, padx=14, pady=12)
        return card

    def _install(self, game: GameDefinition) -> None:
        if self._installing:
            return
        self._installing = True
        self._status.configure(text=f"Installing: {game.name}…", fg=BLUE)
        self._refresh_cards()
        threading.Thread(target=self._install_worker, args=(game,), daemon=True).start()

    def _install_worker(self, game: GameDefinition) -> None:
        try:
            self._installer.install(game)
        except Exception as error:  # package-manager failures need to reach the UI
            self.after(0, self._install_finished, game, error)
            return
        self.after(0, self._install_finished, game, None)

    def _install_finished(self, game: GameDefinition, error: Exception | None) -> None:
        self._installing = False
        if error is not None:
            self._status.configure(text=f"Install failed: {error}", fg=RED)
        elif shutil.which(game.command[0]) is None:
            self._status.configure(text=f"Installed package, but {game.command[0]} was not found", fg=RED)
        else:
            self._status.configure(text=f"Installed: {game.name}", fg=GREEN)
        self._refresh_cards()

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
