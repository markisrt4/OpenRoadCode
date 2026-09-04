# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""! @brief Toolkit-independent values displayed by game frontends."""

from dataclasses import dataclass
from enum import Enum, auto


class GameStatus(Enum):
    """! @brief Lifecycle states visible for a configured game."""

    CHECKING = auto()
    UNAVAILABLE = auto()
    AVAILABLE = auto()
    INSTALLING = auto()
    READY = auto()
    RUNNING = auto()
    ERROR = auto()
    DISABLED = auto()


@dataclass(frozen=True, slots=True)
class GameUiState:
    """! @brief Describe one game as presented by a frontend.

    @param game_id Stable identifier used for semantic UI requests.
    @param name User-visible game name.
    @param description Short user-visible description.
    @param category Filter category used by the frontend.
    @param icon Icon theme name, or None when no icon is configured.
    @param status Current lifecycle state.
    @param backend_id Selected runtime backend, or None when unresolved.
    """

    game_id: str
    name: str
    description: str
    category: str
    icon: str | None
    status: GameStatus
    backend_id: str | None = None
