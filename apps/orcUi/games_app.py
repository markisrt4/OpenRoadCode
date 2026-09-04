# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""orcUi application variant with native games integration."""

from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path

from apps.orcUi.main import GREEN, OrcUiApp
from apps.orcUi.orc_theme import ThemeMode, apply_tk_theme
from controllers.games.game_catalog import load_game_catalog
from controllers.games.game_controller import GameController
from controllers.games.game_installer_factory import create_game_installers
from controllers.games.game_launcher import GameLauncher
from controllers.games.game_types import GameDefinition
from frontends.tk.games import GamesPanel
from frontends.x11.x11_window_embedder import X11WindowEmbedder


class GamesOrcUiApp(OrcUiApp):
    """Extend the cockpit shell with the native games launcher."""

    def __init__(self) -> None:
        self._games_panel: GamesPanel | None = None
        self._games_controller: GameController | None = None
        self._game_launcher = GameLauncher()
        self._game_embedder = X11WindowEmbedder()
        self._game_resize_after_id: str | None = None
        self._pending_game_size: tuple[int, int] | None = None
        super().__init__()

    def _build_side_nav(self) -> None:
        nav = tk.Frame(self._root, bg="#070c11", width=112)
        nav.grid(row=1, column=0, sticky="ns", padx=(8, 0), pady=6)
        nav.grid_propagate(False)
        for item in [
            "HOME", "NAVIGATION", "RADIO", "VEHICLE", "LIGHTING",
            "GAMES", "CONTROLS", "SETTINGS",
        ]:
            button = tk.Button(
                nav, text=item, command=lambda name=item: self._select_nav(name),
                bg="#070c11", fg="#c7cdd2", activebackground="#101820",
                activeforeground=GREEN, relief=tk.FLAT, bd=0,
                font=("Sans", 9), height=3, cursor="hand2",
            )
            button.pack(fill=tk.X, padx=4, pady=2)
            self._nav_buttons[item] = button
        self._paint_nav()

    def _select_nav(self, name: str) -> None:
        if name == "GAMES":
            self._show_games_panel()
            return
        super()._select_nav(name)

    def _clear_content(self) -> None:
        self._stop_game_runtime()
        self._games_controller = None
        self._games_panel = None
        super()._clear_content()

    @staticmethod
    def _load_games() -> list[GameDefinition]:
        config = Path(__file__).resolve().parents[2] / "config" / "games.toml"
        try:
            return load_game_catalog(config)
        except (OSError, KeyError, TypeError, ValueError):
            return []

    def _show_games_panel(self) -> None:
        self._clear_content()
        self._active_nav = "GAMES"
        self._paint_nav()
        panel = GamesPanel(self._content)
        panel.pack(fill=tk.BOTH, expand=True)
        controller = GameController(
            games=self._load_games(),
            installers=create_game_installers(),
            run_work=lambda work: threading.Thread(target=work, daemon=True).start(),
            run_ui=lambda work: self._root.after(0, work),
            launch_game=self._launch_game_runtime,
            stop_game=self._stop_game_runtime,
        )
        self._games_panel = panel
        self._games_controller = controller
        controller.set_games_ui(panel)
        controller.start()
        if self._theme_mode is ThemeMode.LIGHT:
            apply_tk_theme(panel, self._theme_mode)

    def _launch_game_runtime(self, game: GameDefinition, backend) -> None:
        if self._game_launcher.is_running():
            raise RuntimeError("A game is already running")
        if not self._game_embedder.supported():
            raise RuntimeError("Embedded games require xdotool")
        panel = self._games_panel
        if panel is None:
            raise RuntimeError("Games panel is not active")
        host_id, width, height = panel.show_runtime_host(self._resize_game_runtime)
        try:
            command = backend.launch_command(game)
            self._game_launcher.launch(game, command, on_exit=self._game_process_exited)
        except Exception:
            panel.hide_runtime_host()
            raise
        process_id = self._game_launcher.process_id
        if process_id is None:
            self._stop_game_runtime()
            raise RuntimeError(f"{game.name} exited immediately")
        threading.Thread(
            target=self._embed_game_runtime,
            args=(process_id, host_id, width, height),
            daemon=True,
        ).start()

    def _embed_game_runtime(self, process_id: int, host_id: int, width: int, height: int) -> None:
        try:
            self._game_embedder.embed(process_id, host_id, width, height)
        except Exception:
            self._root.after(0, self._game_embed_failed)

    def _game_embed_failed(self) -> None:
        controller = self._games_controller
        if controller is not None:
            controller.request_stop_game()
        else:
            threading.Thread(target=self._stop_game_runtime, daemon=True).start()

    def _game_process_exited(self) -> None:
        """Return spontaneous native-game exits to the controller on Tk."""
        try:
            self._root.after(0, self._finish_game_process_exit)
        except (RuntimeError, tk.TclError):
            pass

    def _finish_game_process_exit(self) -> None:
        self._game_embedder.clear()
        controller = self._games_controller
        if controller is not None:
            controller.request_stop_game()
        else:
            self._finish_stop_game_runtime()

    def _resize_game_runtime(self, width: int, height: int) -> None:
        """Debounce X11 resize work so Configure storms never block Tk."""
        self._pending_game_size = (width, height)
        if self._game_resize_after_id is not None:
            try:
                self._root.after_cancel(self._game_resize_after_id)
            except tk.TclError:
                pass
        self._game_resize_after_id = self._root.after(75, self._dispatch_game_resize)

    def _dispatch_game_resize(self) -> None:
        self._game_resize_after_id = None
        size = self._pending_game_size
        self._pending_game_size = None
        if size is None or self._game_embedder.window_id is None:
            return
        threading.Thread(target=self._game_embedder.resize, args=size, daemon=True).start()

    def _stop_game_runtime(self) -> None:
        """Stop the process; UI restoration is scheduled back onto Tk."""
        self._game_launcher.stop()
        self._game_embedder.clear()
        try:
            self._root.after(0, self._finish_stop_game_runtime)
        except (RuntimeError, tk.TclError):
            pass

    def _finish_stop_game_runtime(self) -> None:
        panel = self._games_panel
        if panel is not None and panel.winfo_exists():
            panel.hide_runtime_host()

    def _shutdown(self) -> None:
        if self._game_resize_after_id is not None:
            try:
                self._root.after_cancel(self._game_resize_after_id)
            except tk.TclError:
                pass
            self._game_resize_after_id = None
        self._game_launcher.stop()
        self._game_embedder.clear()
        super()._shutdown()


def main() -> None:
    """Launch orcUi with native games support."""
    GamesOrcUiApp().run()
