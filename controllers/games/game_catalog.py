"""Load native game definitions from TOML configuration."""

from pathlib import Path
import tomllib

from .game_types import GameDefinition, TermuxProotRuntimeConfig


def load_game_catalog(path: str | Path) -> list[GameDefinition]:
    """Return configured games from *path*."""
    config_path = Path(path)
    with config_path.open("rb") as config_file:
        data = tomllib.load(config_file)

    games: list[GameDefinition] = []
    for entry in data.get("games", []):
        install = entry.get("install", {})
        termux_proot = entry.get("termux_proot", {})
        games.append(
            GameDefinition(
                name=entry["name"],
                command=tuple(entry["command"]),
                description=entry.get("description", ""),
                category=entry.get("category", "casual"),
                icon=entry.get("icon"),
                enabled=entry.get("enabled", True),
                environment=dict(entry.get("environment", {})),
                termux_proot=TermuxProotRuntimeConfig(
                    environment=dict(termux_proot.get("environment", {})),
                    rendering=termux_proot.get("rendering", "auto"),
                    window_name=termux_proot.get("window_name"),
                    window_class=termux_proot.get("window_class"),
                    relax_size_hints=termux_proot.get("relax_size_hints", False),
                ),
                termux_package=install.get("termux_package"),
                termux_dependencies=tuple(install.get("termux_dependencies", [])),
                debian_package=install.get("debian_package"),
            )
        )
    return games
