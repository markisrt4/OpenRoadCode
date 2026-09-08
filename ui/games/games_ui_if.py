# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""! @brief Toolkit-independent display contract for native games."""

from abc import ABC, abstractmethod
from collections.abc import Sequence

from .game_ui_types import GameUiState
from .games_request_handler_if import GamesRequestHandlerIf


class GamesUiIf(ABC):
    """! @brief Display game inventory and accept semantic game requests."""

    @abstractmethod
    def set_games(self, games: Sequence[GameUiState]) -> None:
        """! @brief Replace the complete game display state.

        @param games Ordered game states to display.
        """
        ...

    @abstractmethod
    def set_games_status(self, message: str) -> None:
        """! @brief Set the user-visible games status message.

        @param message Status text to display.
        """
        ...

    @abstractmethod
    def set_games_request_handler(self, handler: GamesRequestHandlerIf | None) -> None:
        """! @brief Set or clear the semantic game request handler.

        @param handler Games request handler, or None to disconnect it.
        """
        ...
