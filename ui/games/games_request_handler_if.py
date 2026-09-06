# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""! @brief Semantic requests emitted by a games frontend."""

from abc import ABC, abstractmethod


class GamesRequestHandlerIf(ABC):
    """! @brief Handle user intent from a games frontend."""

    @abstractmethod
    def request_install_game(self, game_id: str) -> None:
        """! @brief Request installation of one configured game.

        @param game_id Stable game identifier supplied by GamesUiIf state.
        """
        ...

    @abstractmethod
    def request_launch_game(self, game_id: str) -> None:
        """! @brief Request launch of one configured game.

        @param game_id Stable game identifier supplied by GamesUiIf state.
        """
        ...

    @abstractmethod
    def request_stop_game(self) -> None:
        """! @brief Request that the active game be stopped."""
        ...

    @abstractmethod
    def request_refresh_games(self) -> None:
        """! @brief Request a fresh game inventory scan."""
        ...
