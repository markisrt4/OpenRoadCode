# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tk implementation of the toolkit-independent games UI contract."""

from __future__ import annotations

import os
import tkinter as tk
from collections.abc import Callable, Sequence
from pathlib import Path

from ui.games import GameStatus, GameUiState, GamesRequestHandlerIf, GamesUiIf
from ui.theme import ThemeBundle

PAGE_SIZE = 6
FILTERS = (("ALL", "all"), ("CASUAL", "casual"), ("PUZZLE", "puzzle"), ("CARD / BOARD", "card_board"), ("ACTION", "action"))
_ICON_SIZES = (128, 96, 64, 48, 32, 256)


class GamesPanel(tk.Frame, GamesUiIf):
    """Touch-friendly Tk view that renders game state and emits requests."""

    def __init__(self, parent: tk.Misc, *, theme: ThemeBundle) -> None:
        self._theme = theme
        tk.Frame.__init__(self, parent, bg=theme.ui.background)
        self._request_handler: GamesRequestHandlerIf | None = None
        self._games: tuple[GameUiState, ...] = ()
        self._filter = "all"
        self._page = 0
        self._inventory_loading = True
        self._status_message = "Checking games…"
        self._filter_buttons: dict[str, tk.Button] = {}
        self._icon_cache: dict[str, tk.PhotoImage | None] = {}
        self._runtime_host: tk.Frame | None = None
        self._build()

    def set_theme_bundle(self, theme: ThemeBundle) -> None:
        """Apply a CSS-derived theme to the active games surface."""
        self._theme = theme
        if self._runtime_host is not None:
            ui = theme.ui
            self.configure(bg=ui.background)
            self._toolbar.configure(bg=ui.background)
            self._body.configure(bg=ui.background)
            self._runtime_host.configure(
                bg=ui.background,
                highlightbackground=ui.border,
            )
            self._exit_button.configure(
                bg=ui.control_background,
                fg=ui.accent_danger,
                activebackground=ui.control_active,
                activeforeground="#ffffff",
                highlightbackground=ui.accent_danger,
            )
            return
        for child in self.winfo_children():
            child.destroy()
        self._filter_buttons.clear()
        self._build()

    def set_games_request_handler(self, handler: GamesRequestHandlerIf | None) -> None:
        self._request_handler = handler

    def set_games(self, games: Sequence[GameUiState]) -> None:
        self._games = tuple(games)
        if self._runtime_host is None:
            self._refresh_cards()

    def set_games_status(self, message: str) -> None:
        self._status_message = message
        self._inventory_loading = message.startswith(("Checking games", "Refreshing games"))
        self._paint_status()

    def show_runtime_host(self, on_resize: Callable[[int, int], None]) -> tuple[int, int, int]:
        self._clear_body()
        self._filters.pack_forget()
        self._status.pack_forget()
        self._exit_button.pack(side=tk.RIGHT, padx=8)
        self._pager.pack_forget()
        ui = self._theme.ui
        host = tk.Frame(
            self._body,
            bg=ui.background,
            highlightthickness=1,
            highlightbackground=ui.border,
        )
        host.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        host.update_idletasks()
        host.bind("<Configure>", lambda event: on_resize(event.width, event.height))
        self._runtime_host = host
        return host.winfo_id(), host.winfo_width(), host.winfo_height()

    def hide_runtime_host(self) -> None:
        self._runtime_host = None
        self._exit_button.pack_forget()
        self._filters.pack(side=tk.LEFT)
        self._status.pack(side=tk.RIGHT, padx=8)
        self._pager.pack(fill=tk.X, pady=(4, 1))
        self._refresh_cards()

    def _request_exit_game(self) -> None:
        if self._request_handler is not None:
            self._request_handler.request_stop_game()

    def _build(self) -> None:
        ui = self._theme.ui
        self.configure(bg=ui.background)
        self._toolbar = tk.Frame(self, bg=ui.background)
        self._toolbar.pack(fill=tk.X, pady=(2, 6))
        self._filters = tk.Frame(self._toolbar, bg=ui.background)
        self._filters.pack(side=tk.LEFT)
        for label, category in FILTERS:
            button = tk.Button(
                self._filters,
                text=label,
                command=lambda selected=category: self._set_filter(selected),
                relief=tk.FLAT,
                font=("Sans", 9, "bold"),
                padx=11,
                pady=6,
                cursor="hand2",
            )
            button.pack(side=tk.LEFT, padx=(0, 5))
            self._filter_buttons[category] = button
        self._status = tk.Label(
            self._toolbar,
            text=self._status_message,
            bg=ui.background,
            font=("Sans", 10),
        )
        self._status.pack(side=tk.RIGHT, padx=8)
        self._exit_button = tk.Button(
            self._toolbar,
            text="EXIT GAME",
            command=self._request_exit_game,
            bg=ui.control_background,
            fg=ui.accent_danger,
            activebackground=ui.control_active,
            activeforeground="#ffffff",
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=ui.accent_danger,
            font=("Sans", 10, "bold"),
            padx=22,
            pady=6,
            cursor="hand2",
        )
        self._body = tk.Frame(self, bg=ui.background)
        self._body.pack(fill=tk.BOTH, expand=True)
        self._pager = tk.Frame(self, bg=ui.background)
        self._pager.pack(fill=tk.X, pady=(4, 1))
        self._prev_button = self._pager_button("‹ PREV", lambda: self._change_page(-1))
        self._prev_button.pack(side=tk.LEFT, padx=6)
        self._next_button = self._pager_button("NEXT ›", lambda: self._change_page(1))
        self._next_button.pack(side=tk.RIGHT, padx=6)
        self._page_label = tk.Label(
            self._pager,
            text="",
            fg=ui.text_muted,
            bg=ui.background,
            font=("Sans", 9, "bold"),
        )
        self._page_label.pack(expand=True)
        self._update_filter_buttons()
        self._paint_status()
        self._refresh_cards()

    def _pager_button(self, text: str, command: Callable[[], None]) -> tk.Button:
        ui = self._theme.ui
        return tk.Button(
            self._pager,
            text=text,
            command=command,
            bg=ui.control_background,
            fg=ui.control_text,
            activebackground=ui.control_active,
            activeforeground="#ffffff",
            relief=tk.FLAT,
            font=("Sans", 9, "bold"),
            padx=16,
            pady=4,
        )

    def _paint_status(self) -> None:
        ui = self._theme.ui
        message = self._status_message
        if message.startswith(("Install failed", "Launch failed", "Embed failed", "No runtime", "Stop failed")):
            color = ui.accent_danger
        elif message.startswith(("Installing", "Checking", "Refreshing", "Embedding", "Launching", "Stopping")):
            color = ui.accent_primary
        elif message.startswith(("Installed", "Playing")):
            color = ui.accent_success
        else:
            color = ui.text_muted
        self._status.configure(text=message, fg=color, bg=ui.background)

    def _set_filter(self, category: str) -> None:
        if self._runtime_host is not None:
            return
        self._filter = category
        self._page = 0
        self._update_filter_buttons()
        self._refresh_cards()

    def _change_page(self, delta: int) -> None:
        if self._runtime_host is not None:
            return
        games = self._visible_games()
        page_count = max(1, (len(games) + PAGE_SIZE - 1) // PAGE_SIZE)
        self._page = max(0, min(page_count - 1, self._page + delta))
        self._refresh_cards()

    def _update_filter_buttons(self) -> None:
        ui = self._theme.ui
        for category, button in self._filter_buttons.items():
            selected = category == self._filter
            button.configure(
                bg=ui.control_active if selected else ui.control_background,
                fg="#ffffff" if selected else ui.control_text,
                activebackground=ui.control_active,
                activeforeground="#ffffff",
                highlightthickness=1,
                highlightbackground=ui.accent_success if selected else ui.border,
            )

    def _clear_body(self) -> None:
        for child in self._body.winfo_children():
            child.destroy()

    def _visible_games(self) -> list[GameUiState]:
        if self._filter == "all":
            return list(self._games)
        return [game for game in self._games if game.category == self._filter]

    def _show_loading(self) -> None:
        ui = self._theme.ui
        self._page_label.configure(text="")
        self._prev_button.configure(state=tk.DISABLED)
        self._next_button.configure(state=tk.DISABLED)
        tk.Label(
            self._body,
            text="Loading games…",
            fg=ui.text,
            bg=ui.background,
            font=("Sans", 18, "bold"),
        ).place(relx=.5, rely=.45, anchor="center")

    def _refresh_cards(self) -> None:
        self._clear_body()
        if not self._games:
            self._show_loading()
            return
        games = self._visible_games()
        if not games:
            ui = self._theme.ui
            self._page = 0
            self._page_label.configure(text="")
            self._prev_button.configure(state=tk.DISABLED)
            self._next_button.configure(state=tk.DISABLED)
            tk.Label(
                self._body,
                text="No games in this category",
                fg=ui.text_muted,
                bg=ui.background,
                font=("Sans", 18, "bold"),
            ).place(relx=.5, rely=.45, anchor="center")
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
            self._game_card(self._body, game).grid(
                row=index // 2,
                column=index % 2,
                sticky="nsew",
                padx=6,
                pady=5,
            )

    def _find_icon(self, icon_name: str) -> Path | None:
        prefix = Path(os.environ.get("PREFIX", "/usr"))
        for root in (prefix / "share" / "pixmaps", Path("/usr/share/pixmaps")):
            for extension in ("png", "gif"):
                candidate = root / f"{icon_name}.{extension}"
                if candidate.is_file():
                    return candidate
        for root in (prefix / "share" / "icons", Path("/usr/share/icons")):
            for icon_theme in ("hicolor", "breeze", "breeze-dark", "Adwaita"):
                for size in _ICON_SIZES:
                    for context in ("apps", "applications"):
                        for extension in ("png", "gif"):
                            candidate = root / icon_theme / f"{size}x{size}" / context / f"{icon_name}.{extension}"
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
                    image = image.subsample(max(1, (maximum + 55) // 56), max(1, (maximum + 55) // 56))
            except tk.TclError:
                image = None
        self._icon_cache[game.icon] = image
        return image

    def _game_card(self, parent: tk.Misc, game: GameUiState) -> tk.Frame:
        ui = self._theme.ui
        card = tk.Frame(parent, bg=ui.surface, highlightthickness=1, highlightbackground=ui.border)
        card.grid_columnconfigure(1, weight=1)
        label, command, accent = self._action_for(game)
        actionable = command is not None
        icon = self._icon_for(game)
        icon_box = tk.Frame(card, bg=ui.surface, width=64, height=56)
        icon_box.grid(row=0, column=0, rowspan=3, padx=(10, 3), pady=5)
        icon_box.grid_propagate(False)
        icon_label = tk.Label(icon_box, bg=ui.surface)
        if icon is not None:
            icon_label.configure(image=icon)
        else:
            icon_label.configure(text="◈", fg=accent, font=("Sans", 25, "bold"))
        icon_label.place(relx=0.5, rely=0.5, anchor="center")
        available = game.status in (GameStatus.READY, GameStatus.INSTALLING, GameStatus.RUNNING)
        tk.Label(
            card,
            text=game.name,
            fg=ui.text if actionable or available else ui.text_muted,
            bg=ui.surface,
            font=("Sans", 13, "bold"),
        ).grid(row=0, column=1, sticky="sw", padx=6, pady=(5, 0))
        tk.Label(
            card,
            text=game.description,
            fg=ui.text_muted,
            bg=ui.surface,
            font=("Sans", 8),
            anchor="w",
        ).grid(row=1, column=1, sticky="ew", padx=6)
        tk.Label(
            card,
            text=game.status.name,
            fg=accent,
            bg=ui.surface,
            font=("Sans", 8, "bold"),
        ).grid(row=2, column=1, sticky="nw", padx=6, pady=(1, 5))
        tk.Button(
            card,
            text=label,
            command=command,
            state=tk.NORMAL if actionable else tk.DISABLED,
            bg=ui.control_background,
            fg=accent,
            activebackground=ui.control_active,
            activeforeground="#ffffff",
            disabledforeground=accent if game.status in (GameStatus.CHECKING, GameStatus.INSTALLING) else ui.text_muted,
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=accent if actionable else ui.border,
            font=("Sans", 9, "bold"),
            width=11,
            padx=5,
            pady=5,
            cursor="hand2" if actionable else "",
        ).grid(row=0, column=2, rowspan=3, padx=10, pady=9, sticky="e")
        return card

    def _action_for(self, game: GameUiState) -> tuple[str, Callable[[], None] | None, str]:
        ui = self._theme.ui
        if game.status is GameStatus.READY:
            return "PLAY", lambda: self._request_handler.request_launch_game(game.key) if self._request_handler else None, ui.accent_success
        if game.status is GameStatus.RUNNING:
            return "PLAYING", None, ui.accent_success
        if game.status is GameStatus.AVAILABLE:
            return "INSTALL", lambda: self._request_handler.request_install_game(game.key) if self._request_handler else None, ui.accent_primary
        if game.status is GameStatus.INSTALLING:
            return "INSTALLING", None, ui.accent_primary
        if game.status is GameStatus.CHECKING:
            return "CHECKING", None, ui.accent_primary
        return "UNAVAILABLE", None, ui.text_muted
