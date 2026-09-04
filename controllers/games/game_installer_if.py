"""! @brief Interface for platform-specific native game installation and execution."""

from abc import ABC, abstractmethod
from collections.abc import Sequence

from .game_types import GameDefinition


class GameInstallerIf(ABC):
    """! @brief Environment adapter used to query, install, and launch game packages."""

    @property
    @abstractmethod
    def backend_id(self) -> str:
        """! @brief Return the stable identifier used for persistent inventory entries.

        @return Stable backend identifier.
        """

    @abstractmethod
    def is_available(self, game: GameDefinition) -> bool:
        """! @brief Return whether this environment can install a game.

        @param game Configured game definition to query.
        @return True when this backend can install the game, otherwise False.
        """

    @abstractmethod
    def is_installed(self, game: GameDefinition) -> bool:
        """! @brief Return whether a game is installed in this environment.

        @param game Configured game definition to query.
        @return True when this backend already has the game installed, otherwise False.
        """

    @abstractmethod
    def install(self, game: GameDefinition) -> None:
        """! @brief Install a game or raise an exception on failure.

        @param game Configured game definition to install.
        """

    @abstractmethod
    def launch_command(self, game: GameDefinition) -> Sequence[str]:
        """! @brief Build the host command used to launch a game.

        @param game Configured game definition to launch.
        @return Command arguments suitable for the host process launcher.
        """
