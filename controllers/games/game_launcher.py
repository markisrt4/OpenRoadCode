"""Process-backed launcher for native Linux games."""

import os
import subprocess
from typing import Optional

from .game_launcher_if import GameLauncherIf
from .game_types import GameDefinition


class GameLauncher(GameLauncherIf):
    """Launch a configured game as a child process."""

    def __init__(self) -> None:
        self._process: Optional[subprocess.Popen] = None

    def launch(self, game: GameDefinition) -> None:
        if not game.enabled:
            raise ValueError(f"game is disabled: {game.name}")
        if self.is_running():
            raise RuntimeError("a game is already running")

        env = os.environ.copy()
        env.update(game.environment)
        self._process = subprocess.Popen(game.command, env=env)

    def stop(self) -> None:
        if not self.is_running():
            self._process = None
            return

        assert self._process is not None
        self._process.terminate()
        try:
            self._process.wait(timeout=5.0)
        except subprocess.TimeoutExpired:
            self._process.kill()
            self._process.wait()
        finally:
            self._process = None

    def is_running(self) -> bool:
        return self._process is not None and self._process.poll() is None
