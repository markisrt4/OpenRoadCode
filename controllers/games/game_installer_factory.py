"""Select the native game installer for the current runtime."""

from __future__ import annotations

from .debian_game_installer import DebianGameInstaller
from .game_installer_if import GameInstallerIf
from .termux_game_installer import TermuxGameInstaller


def create_game_installer() -> GameInstallerIf:
    """Return the installer appropriate for the current environment."""
    if TermuxGameInstaller.supported():
        return TermuxGameInstaller()
    if DebianGameInstaller.supported():
        return DebianGameInstaller()
    raise RuntimeError("No supported native game package manager is available")
