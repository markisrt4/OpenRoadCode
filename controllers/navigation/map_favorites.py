# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Persistent user-owned map favorites, including Home and Work."""

from __future__ import annotations

import json
from dataclasses import dataclass
from uuid import uuid4

from common.xdg_paths import openroadcode_data_dir
from controllers.cache import PersistentCache, PersistentCacheIf
from ui.navigation import GeoPoint


@dataclass(frozen=True, slots=True)
class MapFavorite:
    """A durable named geographic location."""

    favorite_id: str
    name: str
    position: GeoPoint


class MapFavorites:
    """Persist Home, Work, and arbitrary map favorites."""

    CACHE_KEY = "map-favorites-v1"

    def __init__(self, storage: PersistentCacheIf | None = None) -> None:
        self._storage = storage or PersistentCache(
            openroadcode_data_dir("navigation"), suffix=".json"
        )
        self._home: MapFavorite | None = None
        self._work: MapFavorite | None = None
        self._favorites: tuple[MapFavorite, ...] = ()
        self.load()

    @property
    def home(self) -> MapFavorite | None:
        return self._home

    @property
    def work(self) -> MapFavorite | None:
        return self._work

    @property
    def favorites(self) -> tuple[MapFavorite, ...]:
        return self._favorites

    def load(self) -> None:
        payload = self._storage.get(self.CACHE_KEY)
        if payload is None:
            self._home = None
            self._work = None
            self._favorites = ()
            return
        data = _decode(payload)
        self._home = _favorite_from_record(data.get("home"))
        self._work = _favorite_from_record(data.get("work"))
        raw_favorites = data.get("favorites", [])
        if not isinstance(raw_favorites, list):
            raise ValueError("favorites must be a list")
        self._favorites = tuple(
            favorite for record in raw_favorites
            if (favorite := _favorite_from_record(record)) is not None
        )

    def set_home(self, position: GeoPoint, name: str = "Home") -> MapFavorite:
        self._home = MapFavorite("home", name.strip() or "Home", position)
        self._save()
        return self._home

    def set_work(self, position: GeoPoint, name: str = "Work") -> MapFavorite:
        self._work = MapFavorite("work", name.strip() or "Work", position)
        self._save()
        return self._work

    def add(self, name: str, position: GeoPoint) -> MapFavorite:
        normalized = name.strip()
        if not normalized:
            raise ValueError("favorite name cannot be empty")
        favorite = MapFavorite(str(uuid4()), normalized, position)
        self._favorites = (*self._favorites, favorite)
        self._save()
        return favorite

    def remove(self, favorite_id: str) -> bool:
        updated = tuple(f for f in self._favorites if f.favorite_id != favorite_id)
        if len(updated) == len(self._favorites):
            return False
        self._favorites = updated
        self._save()
        return True

    def _save(self) -> None:
        payload = {
            "version": 1,
            "home": _record(self._home),
            "work": _record(self._work),
            "favorites": [_record(favorite) for favorite in self._favorites],
        }
        self._storage.put(
            self.CACHE_KEY,
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
        )


def _record(favorite: MapFavorite | None) -> dict[str, object] | None:
    if favorite is None:
        return None
    import math
    return {
        "id": favorite.favorite_id,
        "name": favorite.name,
        "latitude": math.degrees(favorite.position.latitude_rad),
        "longitude": math.degrees(favorite.position.longitude_rad),
    }


def _favorite_from_record(record: object) -> MapFavorite | None:
    if record is None:
        return None
    if not isinstance(record, dict):
        raise ValueError("favorite must be an object")
    try:
        favorite_id = str(record["id"]).strip()
        name = str(record["name"]).strip()
        latitude = float(record["latitude"])
        longitude = float(record["longitude"])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("invalid map favorite") from error
    if not favorite_id or not name or not -90.0 <= latitude <= 90.0 or not -180.0 <= longitude <= 180.0:
        raise ValueError("invalid map favorite")
    import math
    return MapFavorite(
        favorite_id,
        name,
        GeoPoint(math.radians(latitude), math.radians(longitude)),
    )


def _decode(payload: bytes) -> dict[str, object]:
    try:
        data = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("invalid map favorites data") from error
    if not isinstance(data, dict) or data.get("version") != 1:
        raise ValueError("unsupported map favorites version")
    return data
