"""Load native game definitions from TOML configuration."""

from pathlib import Path
import tomllib

from .game_types import GameDefinition


def load_game_catalog(path: str | Path) -> list[GameDefinition]:
    """Return configured games from *path*."""
    config_path = Path(path)
    with config_path.open("rb") as config_file:
        data = tomllib.load(config_file)

    games: list[GameDefinition] = []
    for entry in data.get("games", []):
        install = entry.get("install", {})
        games.append(
            GameDefinition(
                name=entry["name"],
                command=tuple(entry["command"]),
                description=entry.get("description", ""),
                enabled=entry.get("enabled", True),
                environment=dict(entry.get("environment", {})),
                termux_package=install.get("termux_package"),
            )
        )
    return games
