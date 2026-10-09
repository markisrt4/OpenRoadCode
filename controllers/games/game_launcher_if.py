"""! @brief Interface for launching native Linux games."""

from abc import ABC, abstractmethod
from collections.abc import Callable, Sequence

from .game_types import GameDefinition


class GameLauncherIf(ABC):
    """! @brief Launch and manage one external game process at a time."""

    @property
    @abstractmethod
    def process_id(self) -> int | None:
        """! @brief Return the active child process identifier.

        @return Process identifier or None when no child is running.
        """

    @abstractmethod
    def launch(
        self, game: GameDefinition, command: Sequence[str] | None = None,
        on_exit: Callable[[], None] | None = None,
    ) -> None:
        """! @brief Launch a game or raise if another game is already running.

        @param game Configured game definition to launch.
        @param command Optional backend-specific command override.
        @param on_exit Callback invoked on the process watcher thread after exit.
        """

    @abstractmethod
    def stop(self) -> None:
        """! @brief Stop the currently running game, if any."""

    @abstractmethod
    def is_running(self) -> bool:
        """! @brief Return whether the launched game process is alive.

        @return True while the launched game process is alive, otherwise False.
        """
