"""Interface for platform-specific native game installation."""

from abc import ABC, abstractmethod

from .game_types import GameDefinition


class GameInstallerIf(ABC):
    """Platform adapter used to query and install game packages."""

    @abstractmethod
    def is_available(self, game: GameDefinition) -> bool:
        """Return whether this platform can install *game*."""

    @abstractmethod
    def install(self, game: GameDefinition) -> None:
        """Install *game* or raise an exception on failure."""
