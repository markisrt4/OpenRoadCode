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

    def __init__(self) -> None:
        self._available_packages: set[str] | None = None

    @property
    def backend_id(self) -> str:
        return "termux"

    @staticmethod
    def supported() -> bool:
        """Return whether the current runtime looks like Termux."""
        return shutil.which("pkg") is not None and "com.termux" in os.environ.get("PREFIX", "")

    def _load_available_packages(self) -> set[str]:
        """Load the Termux package index once instead of spawning apt-cache per game."""
        if self._available_packages is not None:
            return self._available_packages
        result = subprocess.run(
            ["apt-cache", "pkgnames"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
        )
        self._available_packages = set(result.stdout.splitlines()) if result.returncode == 0 else set()
        return self._available_packages

    def _package_available(self, package: str) -> bool:
        return package in self._load_available_packages()

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
        self._available_packages = None

    def launch_command(self, game: GameDefinition) -> Sequence[str]:
        """Return the direct Termux command for *game*."""
        return game.command
