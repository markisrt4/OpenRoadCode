"""Termux package installer for native games."""

from __future__ import annotations

import os
import shutil
import subprocess

from .game_installer_if import GameInstallerIf
from .game_types import GameDefinition


class TermuxGameInstaller(GameInstallerIf):
    """Install games exposed by the configured Termux repositories."""

    @staticmethod
    def supported() -> bool:
        """Return whether the current runtime looks like Termux."""
        return shutil.which("pkg") is not None and "com.termux" in os.environ.get("PREFIX", "")

    def is_available(self, game: GameDefinition) -> bool:
        package = game.termux_package
        if not package or not self.supported():
            return False
        result = subprocess.run(
            ["apt-cache", "show", package],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return result.returncode == 0

    def install(self, game: GameDefinition) -> None:
        package = game.termux_package
        if not package:
            raise ValueError(f"No Termux package configured for {game.name}")
        if not self.supported():
            raise RuntimeError("Termux package manager is not available")
        if not self.is_available(game):
            raise RuntimeError(f"{package} is not available from the configured Termux repositories")
        subprocess.run(["pkg", "install", "-y", package], check=True)
