# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Native games launcher, installer, and X11 host panel for orcUi."""

from __future__ import annotations

import os
import threading
import tkinter as tk
from collections.abc import Callable
from pathlib import Path

from controllers.games.game_catalog import load_game_catalog
from controllers.games.game_installer_factory import create_game_installers
from controllers.games.game_installer_if import GameInstallerIf
from controllers.games.game_launcher import GameLauncher
from controllers.games.game_types import GameDefinition
from frontends.x11.x11_window_embedder import X11WindowEmbedder

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


class GamesPanel(tk.Frame):
    """Touch-friendly launcher, installer, and embedded host for native games."""

    def __init__(self, parent: tk.Misc, on_back: Callable[[], None]) -> None:
        super().__init__(parent, bg=BG)
        self._on_back = on_back
        self._launcher = GameLauncher()
        self._installers = create_game_installers()
        self._embedder = X11WindowEmbedder()
        self._status: tk.Label
        self._body: tk.Frame
        self._page_label: tk.Label
        self._prev_button: tk.Button
        self._next_button: tk.Button
        self._game_host: tk.Frame | None = None
        self._installing_game: GameDefinition | None = None
        self._installing_with: GameInstallerIf | None = None
        self._active_game: GameDefinition | None = None
        self._active_backend: GameInstallerIf | None = None
        self._filter = "all"
        self._page = 0
        self._filter_buttons: dict[str, tk.Button] = {}
        self._icon_cache: dict[str, tk.PhotoImage | None] = {}
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
        toolbar = tk.Frame(self, bg=BG)
        toolbar.pack(fill=tk.X, pady=(2, 6))
        filters = tk.Frame(toolbar, bg=BG)
        filters.pack(side=tk.LEFT)
        for label, category in FILTERS:
            button = tk.Button(filters, text=label, command=lambda selected=category: self._set_filter(selected), relief=tk.FLAT, font=("Sans", 9, "bold"), padx=11, pady=6, cursor="hand2")
            button.pack(side=tk.LEFT, padx=(0, 5))
            self._filter_buttons[category] = button
        self._status = tk.Label(toolbar, text="Choose a game", fg=MUTED, bg=BG, font=("Sans", 10))
        self._status.pack(side=tk.RIGHT, padx=8)
        self._update_filter_buttons()

        self._body = tk.Frame(self, bg=BG)
        self._body.pack(fill=tk.BOTH, expand=True)
        pager = tk.Frame(self, bg=BG)
        pager.pack(fill=tk.X, pady=(4, 1))
        self._prev_button = tk.Button(pager, text="‹ PREV", command=lambda: self._change_page(-1), bg="#101820", fg=TEXT, relief=tk.FLAT, font=("Sans", 9, "bold"), padx=16, pady=4)
        self._prev_button.pack(side=tk.LEFT, padx=6)
        self._next_button = tk.Button(pager, text="NEXT ›", command=lambda: self._change_page(1), bg="#101820", fg=TEXT, relief=tk.FLAT, font=("Sans", 9, "bold"), padx=16, pady=4)
        self._next_button.pack(side=tk.RIGHT, padx=6)
        self._page_label = tk.Label(pager, text="", fg=MUTED, bg=BG, font=("Sans", 9, "bold"))
        self._page_label.pack(expand=True)
        self._refresh_cards()

    def _set_filter(self, category: str) -> None:
        if self._active_game is not None or self._installing_game is not None:
            return
        self._filter = category
        self._page = 0
        self._update_filter_buttons()
        self._refresh_cards()

    def _change_page(self, delta: int) -> None:
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

    def _visible_games(self) -> list[GameDefinition]:
        if self._filter == "all":
            return self._games
        return [game for game in self._games if game.category == self._filter]

    def _installed_backend(self, game: GameDefinition) -> GameInstallerIf | None:
        for installer in self._installers:
            try:
                if installer.is_installed(game):
                    return installer
            except OSError:
                continue
        return None

    def _available_backend(self, game: GameDefinition) -> GameInstallerIf | None:
        for installer in self._installers:
            try:
                if installer.is_available(game):
                    return installer
            except OSError:
                continue
        return None

    def _refresh_cards(self) -> None:
        self._game_host = None
        self._clear_body()
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
        prefix = Path(os.environ.get("PREFIX", "/usr"))
        roots = (prefix / "share" / "icons", prefix / "share" / "pixmaps", Path("/usr/share/icons"), Path("/usr/share/pixmaps"))
        candidates: list[Path] = []
        for root in roots:
            if not root.exists():
                continue
            for extension in ("png", "gif"):
                candidates.extend(root.glob(f"**/{icon_name}.{extension}"))
        if not candidates:
            return None
        def score(path: Path) -> tuple[int, int]:
            text = str(path)
            preferred = 1 if any(size in text for size in ("128x128", "96x96", "64x64", "48x48")) else 0
            return preferred, -len(text)
        return max(candidates, key=score)

    def _icon_for(self, game: GameDefinition) -> tk.PhotoImage | None:
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

    def _game_card(self, parent: tk.Misc, game: GameDefinition) -> tk.Frame:
        card = tk.Frame(parent, bg=PANEL, highlightthickness=1, highlightbackground=BORDER)
        card.grid_columnconfigure(1, weight=1)
        installed_backend = self._installed_backend(game)
        installed = installed_backend is not None
        is_installing = self._installing_game == game
        another_install_running = self._installing_game is not None and not is_installing
        available_backend = None
        if game.enabled and not installed and not is_installing and not another_install_running:
            available_backend = self._available_backend(game)
        installable = available_backend is not None
        if is_installing:
            state, action, command, accent = "INSTALLING", "INSTALLING…", None, BLUE
        elif not game.enabled:
            state, action, command, accent = "DISABLED", "DISABLED", None, MUTED
        elif installed:
            state, action, command, accent = "READY", "PLAY", lambda selected=game, backend=installed_backend: self._launch(selected, backend), GREEN
        elif installable:
            state, action, command, accent = "AVAILABLE", "INSTALL", lambda selected=game, backend=available_backend: self._install(selected, backend), BLUE
        else:
            state, action, command, accent = "UNAVAILABLE", "UNAVAILABLE", None, MUTED
        actionable = command is not None and self._installing_game is None
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
        tk.Label(card, text=game.name, fg=TEXT if actionable or installed or is_installing else MUTED, bg=PANEL, font=("Sans", 13, "bold")).grid(row=0, column=1, sticky="sw", padx=6, pady=(5, 0))
        tk.Label(card, text=game.description, fg=MUTED, bg=PANEL, font=("Sans", 8), anchor="w").grid(row=1, column=1, sticky="ew", padx=6)
        tk.Label(card, text=state, fg=accent, bg=PANEL, font=("Sans", 8, "bold")).grid(row=2, column=1, sticky="nw", padx=6, pady=(1, 5))
        tk.Button(card, text=action, command=command, state=tk.NORMAL if actionable else tk.DISABLED, bg="#102018" if installed else ("#0d1b24" if installable or is_installing else "#11161a"), fg=accent, activebackground="#183024", activeforeground=TEXT, disabledforeground=accent if is_installing else MUTED, relief=tk.FLAT, highlightthickness=1, highlightbackground=accent if actionable or is_installing else BORDER, font=("Sans", 9, "bold"), padx=11, pady=6, cursor="hand2" if actionable else "arrow").grid(row=0, column=2, rowspan=3, padx=10, pady=8)
        return card

    def _show_game_host(self, game: GameDefinition) -> tuple[int, int, int]:
        self._clear_body()
        host = tk.Frame(self._body, bg="#000000", highlightthickness=1, highlightbackground=BORDER)
        host.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        host.update_idletasks()
        self._game_host = host
        self._active_game = game
        host.bind("<Configure>", self._resize_embedded_game)
        return host.winfo_id(), host.winfo_width(), host.winfo_height()

    def _launch(self, game: GameDefinition, backend: GameInstallerIf | None) -> None:
        if backend is None:
            self._status.configure(text=f"No runtime found for {game.name}", fg=RED)
            return
        if self._launcher.is_running():
            self._status.configure(text="A game is already running", fg=RED)
            return
        if not self._embedder.supported():
            self._status.configure(text="Embedded games require xdotool", fg=RED)
            return
        host_id, width, height = self._show_game_host(game)
        self._active_backend = backend
        try:
            self._launcher.launch(game, backend.launch_command(game))
        except (OSError, RuntimeError, ValueError) as error:
            self._active_game = None
            self._active_backend = None
            self._refresh_cards()
            self._status.configure(text=f"Launch failed: {error}", fg=RED)
            return
        process_id = self._launcher.process_id
        if process_id is None:
            self._active_game = None
            self._active_backend = None
            self._refresh_cards()
            self._status.configure(text=f"Launch failed: {game.name} exited immediately", fg=RED)
            return
        self._status.configure(text=f"Embedding: {game.name}…", fg=BLUE)
        threading.Thread(target=self._embed_worker, args=(game, process_id, host_id, width, height), daemon=True).start()

    def _embed_worker(self, game: GameDefinition, process_id: int, host_id: int, width: int, height: int) -> None:
        try:
            self._embedder.embed(process_id, host_id, width, height)
        except Exception as error:
            self.after(0, self._embed_finished, game, error)
            return
        self.after(0, self._embed_finished, game, None)

    def _embed_finished(self, game: GameDefinition, error: Exception | None) -> None:
        if error is not None:
            self._launcher.stop()
            self._embedder.clear()
            self._active_game = None
            self._active_backend = None
            self._refresh_cards()
            self._status.configure(text=f"Embed failed: {error}", fg=RED)
            return
        self._status.configure(text=f"Playing: {game.name}", fg=GREEN)

    def _resize_embedded_game(self, event: tk.Event) -> None:
        if self._embedder.window_id is not None:
            self._embedder.resize(event.width, event.height)

    def _install(self, game: GameDefinition, backend: GameInstallerIf | None) -> None:
        if self._installing_game is not None or backend is None:
            return
        self._installing_game = game
        self._installing_with = backend
        self._status.configure(text=f"Installing: {game.name}…", fg=BLUE)
        self._refresh_cards()
        threading.Thread(target=self._install_worker, args=(game, backend), daemon=True).start()

    def _install_worker(self, game: GameDefinition, backend: GameInstallerIf) -> None:
        try:
            backend.install(game)
        except Exception as error:
            self.after(0, self._install_finished, game, backend, error)
            return
        self.after(0, self._install_finished, game, backend, None)

    def _install_finished(self, game: GameDefinition, backend: GameInstallerIf, error: Exception | None) -> None:
        self._installing_game = None
        self._installing_with = None
        if error is not None:
            self._status.configure(text=f"Install failed: {error}", fg=RED)
        elif not backend.is_installed(game):
            self._status.configure(text=f"Installed package, but {game.command[0]} was not found", fg=RED)
        else:
            self._status.configure(text=f"Installed: {game.name}", fg=GREEN)
        self._refresh_cards()

    def stop(self) -> None:
        """Stop the embedded game launched from this panel."""
        self._launcher.stop()
        self._embedder.clear()
        self._active_game = None
        self._active_backend = None
        self._refresh_cards()
