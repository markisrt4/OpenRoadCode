# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tk implementation of the toolkit-independent games UI contract."""

from __future__ import annotations

import os
import tkinter as tk
from collections.abc import Callable
from pathlib import Path

from ui.games import GameStatus, GameUiState, GamesRequestHandlerIf, GamesUiIf

BG = "#05090d"
PANEL = "#0b1117"
BORDER = "#25313b"
TEXT = "#edf2f5"
MUTED = "#89959e"
GREEN = "#84ce1f"
RED = "#f15a16"
BLUE = "#168bd1"
PAGE_SIZE = 6
FILTERS = (("ALL", "all"), ("CASUAL", "casual"), ("PUZZLE", "puzzle"), ("CARD / BOARD", "card_board"), ("ACTION", "action"))
_ICON_SIZES = (128, 96, 64, 48, 32, 256)


class GamesPanel(tk.Frame, GamesUiIf):
    """Touch-friendly Tk view that renders game state and emits requests."""

    def __init__(self, parent: tk.Misc) -> None:
        tk.Frame.__init__(self, parent, bg=BG)
        self._request_handler: GamesRequestHandlerIf | None = None
        self._games: tuple[GameUiState, ...] = ()
        self._status: tk.Label
        self._toolbar: tk.Frame
        self._filters: tk.Frame
        self._exit_button: tk.Button
        self._body: tk.Frame
        self._pager: tk.Frame
        self._page_label: tk.Label
        self._prev_button: tk.Button
        self._next_button: tk.Button
        self._runtime_host: tk.Frame | None = None
        self._filter = "all"
        self._page = 0
        self._initial_loading = True
        self._filter_buttons: dict[str, tk.Button] = {}
        self._icon_cache: dict[str, tk.PhotoImage | None] = {}
        self._build()

    def set_games_request_handler(self, handler: GamesRequestHandlerIf | None) -> None:
        self._request_handler = handler

    def set_games(self, games: tuple[GameUiState, ...]) -> None:
        self._games = tuple(games)
        if self._runtime_host is None:
            self._refresh_cards()

    def set_games_status(self, message: str) -> None:
        was_loading = self._initial_loading
        self._initial_loading = message.startswith(("Checking games", "Refreshing games"))
        if message.startswith(("Install failed", "Launch failed", "Embed failed", "No runtime", "Stop failed")):
            color = RED
        elif message.startswith(("Installing", "Checking", "Refreshing", "Embedding", "Launching", "Stopping")):
            color = BLUE
        elif message.startswith(("Installed", "Playing")):
            color = GREEN
        else:
            color = MUTED
        self._status.configure(text=message, fg=color)
        if self._runtime_host is None and was_loading != self._initial_loading:
            self._refresh_cards()

    def show_runtime_host(self, on_resize: Callable[[int, int], None]) -> tuple[int, int, int]:
        """Replace game cards with a native-window host and enter kiosk mode."""
        self._clear_body()
        self._filters.pack_forget()
        self._status.pack_forget()
        self._exit_button.pack(side=tk.RIGHT, padx=8)
        self._pager.pack_forget()
        host = tk.Frame(self._body, bg="#000000", highlightthickness=1, highlightbackground=BORDER)
        host.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        host.update_idletasks()
        host.bind("<Configure>", lambda event: on_resize(event.width, event.height))
        self._runtime_host = host
        return host.winfo_id(), host.winfo_width(), host.winfo_height()

    def hide_runtime_host(self) -> None:
        """Leave kiosk mode and restore the normal games browser."""
        self._runtime_host = None
        self._exit_button.pack_forget()
        self._filters.pack(side=tk.LEFT)
        self._status.pack(side=tk.RIGHT, padx=8)
        self._pager.pack(fill=tk.X, pady=(4, 1))
        self._refresh_cards()

    def _request_exit_game(self) -> None:
        handler = self._request_handler
        if handler is not None:
            handler.request_stop_game()

    def _build(self) -> None:
        self._toolbar = tk.Frame(self, bg=BG)
        self._toolbar.pack(fill=tk.X, pady=(2, 6))
        self._filters = tk.Frame(self._toolbar, bg=BG)
        self._filters.pack(side=tk.LEFT)
        for label, category in FILTERS:
            button = tk.Button(self._filters, text=label, command=lambda selected=category: self._set_filter(selected), relief=tk.FLAT, font=("Sans", 9, "bold"), padx=11, pady=6, cursor="hand2")
            button.pack(side=tk.LEFT, padx=(0, 5))
            self._filter_buttons[category] = button
        self._status = tk.Label(self._toolbar, text="Checking games…", fg=BLUE, bg=BG, font=("Sans", 10))
        self._status.pack(side=tk.RIGHT, padx=8)
        self._exit_button = tk.Button(
            self._toolbar,
            text="EXIT GAME",
            command=self._request_exit_game,
            bg="#29110d",
            fg=RED,
            activebackground="#3b1811",
            activeforeground=TEXT,
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=RED,
            font=("Sans", 10, "bold"),
            padx=22,
            pady=6,
            cursor="hand2",
        )
        self._update_filter_buttons()
        self._body = tk.Frame(self, bg=BG)
        self._body.pack(fill=tk.BOTH, expand=True)
        self._pager = tk.Frame(self, bg=BG)
        self._pager.pack(fill=tk.X, pady=(4, 1))
        self._prev_button = tk.Button(self._pager, text="‹ PREV", command=lambda: self._change_page(-1), bg="#101820", fg=TEXT, relief=tk.FLAT, font=("Sans", 9, "bold"), padx=16, pady=4)
        self._prev_button.pack(side=tk.LEFT, padx=6)
        self._next_button = tk.Button(self._pager, text="NEXT ›", command=lambda: self._change_page(1), bg="#101820", fg=TEXT, relief=tk.FLAT, font=("Sans", 9, "bold"), padx=16, pady=4)
        self._next_button.pack(side=tk.RIGHT, padx=6)
        self._page_label = tk.Label(self._pager, text="", fg=MUTED, bg=BG, font=("Sans", 9, "bold"))
        self._page_label.pack(expand=True)
        self._refresh_cards()

    def _set_filter(self, category: str) -> None:
        if self._runtime_host is not None or self._initial_loading:
            return
        self._filter = category
        self._page = 0
        self._update_filter_buttons()
        self._refresh_cards()

    def _change_page(self, delta: int) -> None:
        if self._runtime_host is not None or self._initial_loading:
            return
        games = self._visible_games()
        page_count = max(1, (len(games) + PAGE_SIZE - 1) // PAGE_SIZE)
        self._page = max(0, min(page_count - 1, self._page + delta))
        self._refresh_cards()

    def _update_filter_buttons(self) -> None:
        for category, button in self._filter_buttons.items():
            selected = category == self._filter
            button.configure(bg="#17300f" if selected else "#101820", fg=GREEN if selected else TEXT, activebackground="#214019" if selected else "#18232c", activeforeground=TEXT, highlightthickness=1, highlightbackground=GREEN if selected else BORDER)

    def _clear_body(self) -> None:
        for child in self._body.winfo_children():
            child.destroy()

    def _visible_games(self) -> list[GameUiState]:
        if self._filter == "all":
            return list(self._games)
        return [game for game in self._games if game.category == self._filter]

    def _show_loading(self) -> None:
        self._page_label.configure(text="")
        self._prev_button.configure(state=tk.DISABLED)
        self._next_button.configure(state=tk.DISABLED)
        tk.Label(self._body, text="Loading games…", fg=TEXT, bg=BG, font=("Sans", 18, "bold")).place(relx=.5, rely=.45, anchor="center")

    def _refresh_cards(self) -> None:
        self._clear_body()
        if self._initial_loading:
            self._show_loading()
            return
        games = self._visible_games()
        if not games:
            self._page = 0
            self._page_label.configure(text="")
            self._prev_button.configure(state=tk.DISABLED)
            self._next_button.configure(state=tk.DISABLED)
            tk.Label(self._body, text="No games in this category", fg=MUTED, bg=BG, font=("Sans", 18, "bold")).place(relx=.5, rely=.45, anchor="center")
            return
        page_count = max(1, (len(games) + PAGE_SIZE - 1) // PAGE_SIZE)
        self._page = min(self._page, page_count - 1)
        start = self._page * PAGE_SIZE
        page_games = games[start:start + PAGE_SIZE]
        self._page_label.configure(text=f"{self._page + 1} / {page_count}" if page_count > 1 else "")
        self._prev_button.configure(state=tk.NORMAL if self._page > 0 else tk.DISABLED)
        self._next_button.configure(state=tk.NORMAL if self._page + 1 < page_count else tk.DISABLED)
        for column in range(2):
            self._body.grid_columnconfigure(column, weight=1, uniform="game")
        for row in range(3):
            self._body.grid_rowconfigure(row, weight=1, uniform="game")
        for index, game in enumerate(page_games):
            self._game_card(self._body, game).grid(row=index // 2, column=index % 2, sticky="nsew", padx=6, pady=5)

    def _find_icon(self, icon_name: str) -> Path | None:
        """Find a desktop icon without recursively walking the whole icon tree."""
        prefix = Path(os.environ.get("PREFIX", "/usr"))
        pixmap_roots = (prefix / "share" / "pixmaps", Path("/usr/share/pixmaps"))
        for root in pixmap_roots:
            for extension in ("png", "gif"):
                candidate = root / f"{icon_name}.{extension}"
                if candidate.is_file():
                    return candidate
        icon_roots = (prefix / "share" / "icons", Path("/usr/share/icons"))
        for root in icon_roots:
            for theme in ("hicolor", "breeze", "breeze-dark", "Adwaita"):
                for size in _ICON_SIZES:
                    for context in ("apps", "applications"):
                        for extension in ("png", "gif"):
                            candidate = root / theme / f"{size}x{size}" / context / f"{icon_name}.{extension}"
                            if candidate.is_file():
                                return candidate
        return None

    def _icon_for(self, game: GameUiState) -> tk.PhotoImage | None:
        if not game.icon:
            return None
        if game.icon in self._icon_cache:
            return self._icon_cache[game.icon]
        path = self._find_icon(game.icon)
        image: tk.PhotoImage | None = None
        if path is not None:
            try:
                image = tk.PhotoImage(file=str(path))
                maximum = max(image.width(), image.height())
                if maximum > 56:
                    factor = max(1, (maximum + 55) // 56)
                    image = image.subsample(factor, factor)
            except tk.TclError:
                image = None
        self._icon_cache[game.icon] = image
        return image

    def _game_card(self, parent: tk.Misc, game: GameUiState) -> tk.Frame:
        card = tk.Frame(parent, bg=PANEL, highlightthickness=1, highlightbackground=BORDER)
        card.grid_columnconfigure(1, weight=1)
        label, command, accent = self._action_for(game)
        actionable = command is not None
        icon = self._icon_for(game)
        icon_box = tk.Frame(card, bg=PANEL, width=64, height=56)
        icon_box.grid(row=0, column=0, rowspan=3, padx=(10, 3), pady=5)
        icon_box.grid_propagate(False)
        icon_label = tk.Label(icon_box, bg=PANEL)
        if icon is not None:
            icon_label.configure(image=icon)
        else:
            icon_label.configure(text="◈", fg=accent, font=("Sans", 25, "bold"))
        icon_label.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(card, text=game.name, fg=TEXT if actionable or game.status in (GameStatus.READY, GameStatus.INSTALLING, GameStatus.RUNNING) else MUTED, bg=PANEL, font=("Sans", 13, "bold")).grid(row=0, column=1, sticky="sw", padx=6, pady=(5, 0))
        tk.Label(card, text=game.description, fg=MUTED, bg=PANEL, font=("Sans", 8), anchor="w").grid(row=1, column=1, sticky="ew", padx=6)
        tk.Label(card, text=game.status.name, fg=accent, bg=PANEL, font=("Sans", 8, "bold")).grid(row=2, column=1, sticky="nw", padx=6, pady=(1, 5))
        tk.Button(card, text=label, command=command, state=tk.NORMAL if actionable else tk.DISABLED, bg="#102018" if game.status in (GameStatus.READY, GameStatus.RUNNING) else ("#0d1b24" if game.status in (GameStatus.AVAILABLE, GameStatus.CHECKING, GameStatus.INSTALLING) else "#11161a"), fg=accent, activebackground="#183024", activeforeground=TEXT, disabledforeground=accent if game.status in (GameStatus.CHECKING, GameStatus.INSTALLING) else MUTED, relief=tk.FLAT, highlightthickness=1, highlightbackground=accent if actionable or game.status in (GameStatus.CHECKING, GameStatus.INSTALLING) else BORDER, font=("Sans", 9, "bold"), padx=11, pady=6, cursor="hand2" if actionable else "arrow").grid(row=0, column=2, rowspan=3, padx=10, pady=8)
        return card

    def _action_for(self, game: GameUiState) -> tuple[str, object | None, str]:
        handler = self._request_handler
        if game.status == GameStatus.READY:
            return "PLAY", (lambda: handler.request_launch_game(game.game_id)) if handler else None, GREEN
        if game.status == GameStatus.AVAILABLE:
            return "INSTALL", (lambda: handler.request_install_game(game.game_id)) if handler else None, BLUE
        if game.status == GameStatus.RUNNING:
            return "STOP", handler.request_stop_game if handler else None, GREEN
        if game.status == GameStatus.INSTALLING:
            return "INSTALLING…", None, BLUE
        if game.status == GameStatus.CHECKING:
            return "CHECKING…", None, BLUE
        if game.status == GameStatus.ERROR:
            return "ERROR", None, RED
        if game.status == GameStatus.DISABLED:
            return "DISABLED", None, MUTED
        return "UNAVAILABLE", None, MUTED
