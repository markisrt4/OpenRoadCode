"""! @brief Interface for launching native Linux games."""

from abc import ABC, abstractmethod

from .game_types import GameDefinition


class GameLauncherIf(ABC):
    """! @brief Launch and manage one external game process at a time."""

    @abstractmethod
    def launch(self, game: GameDefinition) -> None:
        """! @brief Launch a game or raise if another game is already running.

        @param game Configured game definition to launch.
        """

    @abstractmethod
    def stop(self) -> None:
        """! @brief Stop the currently running game, if any."""

    @abstractmethod
    def is_running(self) -> bool:
        """! @brief Return whether the launched game process is alive.

        @return True while the launched game process is alive, otherwise False.
        """
