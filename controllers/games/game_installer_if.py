"""Interface for platform-specific native game installation and execution."""

from abc import ABC, abstractmethod
from collections.abc import Sequence

from .game_types import GameDefinition


class GameInstallerIf(ABC):
    """Environment adapter used to query, install, and launch game packages."""

    @abstractmethod
    def is_available(self, game: GameDefinition) -> bool:
        """Return whether this environment can install *game*."""

    @abstractmethod
    def is_installed(self, game: GameDefinition) -> bool:
        """Return whether *game* is installed in this environment."""

    @abstractmethod
    def install(self, game: GameDefinition) -> None:
        """Install *game* or raise an exception on failure."""

    @abstractmethod
    def launch_command(self, game: GameDefinition) -> Sequence[str]:
        """Return the host command used to launch *game* in this environment."""
