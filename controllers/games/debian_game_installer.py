"""Debian package installer for native games."""

from __future__ import annotations

import subprocess

from .debian_command_runner import DebianCommandRunner
from .game_installer_if import GameInstallerIf
from .game_types import GameDefinition


class DebianGameInstaller(GameInstallerIf):
    """Install games from Debian regardless of how Debian is hosted."""

    def __init__(self) -> None:
        self._runner = DebianCommandRunner()

    @staticmethod
    def supported() -> bool:
        """Return whether a Debian environment is available."""
        return DebianCommandRunner.supported()

    def _package_available(self, package: str) -> bool:
        result = self._runner.run(
            ["apt-cache", "policy", package],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return False
        for line in result.stdout.splitlines():
            stripped = line.strip()
            if stripped.startswith("Candidate:"):
                candidate = stripped.partition(":")[2].strip()
                return bool(candidate and candidate != "(none)")
        return False

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
            raise RuntimeError("Debian is not available")
        if not self.is_available(game):
            raise RuntimeError(f"{package} is not available from the configured Debian repositories")
        self._runner.run(["apt-get", "install", "-y", package], check=True)
