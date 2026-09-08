"""Process-backed launcher for native Linux games."""

import os
import subprocess
import threading
from collections.abc import Callable, Sequence
from typing import Optional

from .game_launcher_if import GameLauncherIf
from .game_types import GameDefinition


class GameLauncher(GameLauncherIf):
    """Launch a configured game as a child process."""

    def __init__(self) -> None:
        self._process: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()

    @property
    def process_id(self) -> int | None:
        """Return the active child process id, if one exists."""
        with self._lock:
            process = self._process
        if process is None or process.poll() is not None:
            return None
        return process.pid

    def launch(
        self,
        game: GameDefinition,
        command: Sequence[str] | None = None,
        on_exit: Callable[[], None] | None = None,
    ) -> None:
        if not game.enabled:
            raise ValueError(f"game is disabled: {game.name}")
        if self.is_running():
            raise RuntimeError("a game is already running")

        env = os.environ.copy()
        env.update(game.environment)
        process = subprocess.Popen(tuple(command) if command is not None else game.command, env=env)
        with self._lock:
            self._process = process

        if on_exit is not None:
            threading.Thread(
                target=self._wait_for_exit,
                args=(process, on_exit),
                daemon=True,
            ).start()

    def _wait_for_exit(self, process: subprocess.Popen, on_exit: Callable[[], None]) -> None:
        process.wait()
        with self._lock:
            if self._process is process:
                self._process = None
        on_exit()

    def stop(self) -> None:
        with self._lock:
            process = self._process
        if process is None or process.poll() is not None:
            with self._lock:
                if self._process is process:
                    self._process = None
            return

        process.terminate()
        try:
            process.wait(timeout=5.0)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        finally:
            with self._lock:
                if self._process is process:
                    self._process = None

    def is_running(self) -> bool:
        with self._lock:
            process = self._process
        return process is not None and process.poll() is None
