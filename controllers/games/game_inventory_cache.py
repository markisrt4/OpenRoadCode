"""Persistent cache of games known to be installed by a game backend."""

from __future__ import annotations

import json
import os
from pathlib import Path


class GameInventoryCache:
    """Persist installed game/backend associations across ORC runs."""

    VERSION = 1

    def __init__(self, path: Path | None = None) -> None:
        cache_home = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
        self._path = path or cache_home / "openroadcode" / "games" / "inventory.json"

    def load(self) -> dict[str, str]:
        """Return cached game name to backend ID mappings."""
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, TypeError):
            return {}
        if not isinstance(data, dict) or data.get("version") != self.VERSION:
            return {}
        games = data.get("games", {})
        if not isinstance(games, dict):
            return {}
        return {str(name): str(backend) for name, backend in games.items() if backend}

    def save(self, games: dict[str, str]) -> None:
        """Persist game name to backend ID mappings atomically."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps({"version": self.VERSION, "games": games}, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(self._path)
