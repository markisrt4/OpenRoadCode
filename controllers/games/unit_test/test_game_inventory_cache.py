from __future__ import annotations

import json
from pathlib import Path

from controllers.games.game_inventory_cache import GameInventoryCache


def test_missing_cache_loads_empty(tmp_path: Path) -> None:
    cache = GameInventoryCache(tmp_path / "inventory.json")

    assert cache.load() == {}


def test_cache_round_trip_persists_backend_ids(tmp_path: Path) -> None:
    path = tmp_path / "inventory.json"
    cache = GameInventoryCache(path)
    expected = {
        "KMines": "termux",
        "SuperTuxKart": "debian",
    }

    cache.save(expected)

    assert cache.load() == expected
    assert json.loads(path.read_text(encoding="utf-8")) == {
        "version": GameInventoryCache.VERSION,
        "games": expected,
    }


def test_save_replaces_existing_inventory(tmp_path: Path) -> None:
    path = tmp_path / "inventory.json"
    cache = GameInventoryCache(path)
    cache.save({"KMines": "termux"})

    cache.save({"KMines": "termux", "KPatience": "debian"})

    assert cache.load() == {
        "KMines": "termux",
        "KPatience": "debian",
    }
    assert not path.with_suffix(".tmp").exists()


def test_corrupt_cache_is_ignored(tmp_path: Path) -> None:
    path = tmp_path / "inventory.json"
    path.write_text("{ definitely not json", encoding="utf-8")

    assert GameInventoryCache(path).load() == {}


def test_unknown_cache_version_is_ignored(tmp_path: Path) -> None:
    path = tmp_path / "inventory.json"
    path.write_text(
        json.dumps({"version": GameInventoryCache.VERSION + 1, "games": {"KMines": "termux"}}),
        encoding="utf-8",
    )

    assert GameInventoryCache(path).load() == {}


def test_invalid_games_payload_is_ignored(tmp_path: Path) -> None:
    path = tmp_path / "inventory.json"
    path.write_text(
        json.dumps({"version": GameInventoryCache.VERSION, "games": ["KMines"]}),
        encoding="utf-8",
    )

    assert GameInventoryCache(path).load() == {}
