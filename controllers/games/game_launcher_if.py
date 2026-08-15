"""Interface for launching native Linux games."""

from abc import ABC, abstractmethod

from .game_types import GameDefinition


class GameLauncherIf(ABC):
    """Launch and manage one external game process at a time."""

    @abstractmethod
    def launch(self, game: GameDefinition) -> None:
        """Launch *game* or raise if another game is already running."""

    @abstractmethod
    def stop(self) -> None:
        """Stop the currently running game, if any."""

    @abstractmethod
    def is_running(self) -> bool:
        """Return True while the launched game process is alive."""
