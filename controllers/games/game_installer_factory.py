"""Select native game installers available to the current runtime."""

from __future__ import annotations

from .debian_game_installer import DebianGameInstaller
from .game_installer_if import GameInstallerIf
from .termux_game_installer import TermuxGameInstaller


def create_game_installers() -> tuple[GameInstallerIf, ...]:
    """Return every game installer reachable from the current environment."""
    installers: list[GameInstallerIf] = []
    if TermuxGameInstaller.supported():
        installers.append(TermuxGameInstaller())
    if DebianGameInstaller.supported():
        installers.append(DebianGameInstaller())
    return tuple(installers)


def create_game_installer() -> GameInstallerIf:
    """Return the preferred installer for compatibility with existing callers."""
    installers = create_game_installers()
    if not installers:
        raise RuntimeError("No supported native game package manager is available")
    return installers[0]
