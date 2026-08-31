"""Termux package installer for native games."""

from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Sequence

from .game_installer_if import GameInstallerIf
from .game_types import GameDefinition


class TermuxGameInstaller(GameInstallerIf):
    """Install and execute games exposed by the configured Termux repositories."""

    @property
    def backend_id(self) -> str:
        return "termux"

    @staticmethod
    def supported() -> bool:
        """Return whether the current runtime looks like Termux."""
        return shutil.which("pkg") is not None and "com.termux" in os.environ.get("PREFIX", "")

    @staticmethod
    def _package_available(package: str) -> bool:
        result = subprocess.run(
            ["apt-cache", "show", package],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return result.returncode == 0

    def is_available(self, game: GameDefinition) -> bool:
        package = game.termux_package
        if not package or not self.supported():
            return False
        return self._package_available(package) and all(
            self._package_available(dependency) for dependency in game.termux_dependencies
        )

    def is_installed(self, game: GameDefinition) -> bool:
        """Return whether the game's executable is available in Termux."""
        return self.supported() and shutil.which(game.command[0]) is not None

    def install(self, game: GameDefinition) -> None:
        package = game.termux_package
        if not package:
            raise ValueError(f"No Termux package configured for {game.name}")
        if not self.supported():
            raise RuntimeError("Termux package manager is not available")
        if not self.is_available(game):
            raise RuntimeError(f"{package} or one of its dependencies is not available from the configured Termux repositories")
        packages = [package, *game.termux_dependencies]
        subprocess.run(["pkg", "install", "-y", *packages], check=True)

    def launch_command(self, game: GameDefinition) -> Sequence[str]:
        """Return the direct Termux command for *game*."""
        return game.command
