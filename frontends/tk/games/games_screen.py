# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Contract-based Tk screen for native games."""

from __future__ import annotations

import threading
from collections.abc import Callable
from pathlib import Path

import tkinter as tk

from controllers.games.game_catalog import load_game_catalog
from controllers.games.game_controller import GameController
from controllers.games.game_installer_factory import create_game_installers
from controllers.games.game_installer_if import GameInstallerIf
from controllers.games.game_launcher import GameLauncher
from controllers.games.game_types import GameDefinition
from frontends.tk.tk_screen import TkScreen
from frontends.tk.tk_screen_host_if import TkScreenHostIf
from frontends.x11.x11_window_embedder import X11WindowEmbedder
from ui.screen_ui_if import ScreenId
from ui.theme import ThemeBundle, ThemeMode

from .games_panel import GamesPanel


class GamesScreen(TkScreen):
    """Compose the Games UI, controller, and native runtime behind ScreenUiIf."""

    def __init__(
        self,
        host: TkScreenHostIf,
        *,
        theme_bundle: Callable[[], ThemeBundle],
        theme_mode: Callable[[], ThemeMode],
    ) -> None:
        super().__init__(ScreenId("games"))
        self._host = host
        self._theme_bundle = theme_bundle
        self._theme_mode = theme_mode
        self._panel: GamesPanel | None = None
        self._controller: GameController | None = None
        self._launcher = GameLauncher()
        self._embedder = X11WindowEmbedder()
        self._resize_callback_id: object | None = None
        self._pending_size: tuple[int, int] | None = None

    def show(self) -> None:
        self.hide()
        self._host.activate_screen(self)
        self._host.clear_screen_content()
        self._host.set_screen_title("GAMES")

        panel = GamesPanel(self._host.screen_parent, theme=self._theme_bundle())
        panel.pack(fill=tk.BOTH, expand=True)

        controller = GameController(
            games=self._load_games(),
            installers=create_game_installers(),
            run_work=lambda work: threading.Thread(target=work, daemon=True).start(),
            run_ui=lambda work: self._host.schedule_ui_callback(0, work),
            launch_game=self._launch_runtime,
            stop_game=self._stop_runtime,
        )
        self._panel = panel
        self._controller = controller
        controller.set_games_ui(panel)
        controller.start()

    def hide(self) -> None:
        controller = self._controller
        if controller is not None:
            controller.set_games_ui(None)
        self._controller = None
        self._cancel_resize()
        self._launcher.stop()
        self._embedder.clear()
        self._panel = None

    def set_theme_mode(self, mode: ThemeMode) -> None:
        """Apply the current CSS-derived theme bundle to Games."""
        del mode
        panel = self._panel
        if panel is not None and panel.winfo_exists():
            panel.set_theme_bundle(self._theme_bundle())

    def shutdown(self) -> None:
        self.hide()

    @staticmethod
    def _load_games() -> list[GameDefinition]:
        config = Path(__file__).resolve().parents[3] / "config" / "games.toml"
        try:
            return load_game_catalog(config)
        except (OSError, KeyError, TypeError, ValueError):
            return []

    def _launch_runtime(self, game: GameDefinition, backend: GameInstallerIf) -> None:
        if self._launcher.is_running():
            raise RuntimeError("A game is already running")
        if not self._embedder.supported():
            raise RuntimeError("Embedded games require xdotool")
        panel = self._panel
        if panel is None:
            raise RuntimeError("Games screen is not active")

        host_id, width, height = panel.show_runtime_host(self._resize_runtime)
        try:
            self._launcher.launch(game, backend.launch_command(game), on_exit=self._process_exited)
        except Exception:
            panel.hide_runtime_host()
            raise

        process_id = self._launcher.process_id
        if process_id is None:
            self._stop_runtime()
            raise RuntimeError(f"{game.name} exited immediately")
        threading.Thread(
            target=self._embed_runtime,
            args=(process_id, host_id, width, height),
            daemon=True,
        ).start()

    def _embed_runtime(self, process_id: int, host_id: int, width: int, height: int) -> None:
        try:
            self._embedder.embed(process_id, host_id, width, height)
        except Exception:
            self._host.schedule_ui_callback(0, self._embed_failed)

    def _embed_failed(self) -> None:
        controller = self._controller
        if controller is not None:
            controller.request_stop_game()
        else:
            threading.Thread(target=self._stop_runtime, daemon=True).start()

    def _process_exited(self) -> None:
        try:
            self._host.schedule_ui_callback(0, self._finish_process_exit)
        except (RuntimeError, tk.TclError):
            pass

    def _finish_process_exit(self) -> None:
        self._embedder.clear()
        controller = self._controller
        if controller is not None:
            controller.request_stop_game()
        else:
            self._finish_stop_runtime()

    def _resize_runtime(self, width: int, height: int) -> None:
        self._pending_size = (width, height)
        self._cancel_resize()
        self._resize_callback_id = self._host.schedule_ui_callback(75, self._dispatch_resize)

    def _cancel_resize(self) -> None:
        callback_id = self._resize_callback_id
        self._resize_callback_id = None
        if callback_id is None:
            return
        try:
            self._host.cancel_ui_callback(callback_id)
        except (RuntimeError, tk.TclError):
            pass

    def _dispatch_resize(self) -> None:
        self._resize_callback_id = None
        size = self._pending_size
        self._pending_size = None
        if size is None or self._embedder.window_id is None:
            return
        threading.Thread(target=self._embedder.resize, args=size, daemon=True).start()

    def _stop_runtime(self) -> None:
        self._launcher.stop()
        self._embedder.clear()
        try:
            self._host.schedule_ui_callback(0, self._finish_stop_runtime)
        except (RuntimeError, tk.TclError):
            pass

    def _finish_stop_runtime(self) -> None:
        panel = self._panel
        if panel is not None and panel.winfo_exists():
            panel.hide_runtime_host()
