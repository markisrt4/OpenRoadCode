"""Native Linux game launching support."""

from .game_launcher import GameLauncher
from .game_types import GameDefinition

__all__ = ["GameDefinition", "GameLauncher"]
