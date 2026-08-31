"""Debian package installer for native games."""

from __future__ import annotations

import shutil
import subprocess

from .game_installer_if import GameInstallerIf
from .game_types import GameDefinition


class DebianGameInstaller(GameInstallerIf):
    """Install games exposed by configured Debian APT repositories."""

    @staticmethod
    def supported() -> bool:
        """Return whether a Debian-style package manager is available."""
        return shutil.which("apt-get") is not None and shutil.which("dpkg-query") is not None

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
        package = game.debian_package
        if not package or not self.supported():
            return False
        return self._package_available(package)

    def install(self, game: GameDefinition) -> None:
        package = game.debian_package
        if not package:
            raise ValueError(f"No Debian package configured for {game.name}")
        if not self.supported():
            raise RuntimeError("Debian package manager is not available")
        if not self.is_available(game):
            raise RuntimeError(f"{package} is not available from the configured Debian repositories")
        subprocess.run(["apt-get", "install", "-y", package], check=True)
