# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Persistent, user-owned streaming-radio favorite station identifiers."""

from __future__ import annotations

import json
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib

from common.xdg_paths import openroadcode_data_dir, xdg_config_home
from controllers.cache import PersistentCache, PersistentCacheIf


class StreamingRadioFavorites:
    """Persist Radio Browser station UUIDs through the shared byte store."""

    CACHE_KEY = "streaming-radio-favorites-v1"

    def __init__(
        self,
        storage: PersistentCacheIf | None = None,
        *,
        legacy_path: Path | None = None,
    ) -> None:
        self._storage = storage or PersistentCache(
            openroadcode_data_dir("radio"), suffix=".json"
        )
        self._legacy_path = legacy_path or (
            xdg_config_home() / "openroadcode" / "streaming_radio.toml"
        )
        self._station_ids: tuple[str, ...] = ()
        self.load()

    @property
    def station_ids(self) -> frozenset[str]:
        return frozenset(self._station_ids)

    @property
    def ordered_station_ids(self) -> tuple[str, ...]:
        return self._station_ids

    def load(self) -> None:
        payload = self._storage.get(self.CACHE_KEY)
        if payload is not None:
            self._station_ids = _decode_station_ids(payload)
            return

        migrated = self._load_legacy_ids()
        if migrated:
            self._save(migrated)
            self._station_ids = migrated
            return
        self._station_ids = ()

    def toggle(self, station_id: str) -> bool:
        normalized = station_id.strip()
        if not normalized:
            raise ValueError("station_id cannot be empty")

        updated = list(self._station_ids)
        if normalized in updated:
            updated.remove(normalized)
            favorite = False
        else:
            updated.append(normalized)
            favorite = True

        serialized = tuple(updated)
        self._save(serialized)
        self._station_ids = serialized
        return favorite

    def _save(self, station_ids: tuple[str, ...]) -> None:
        payload = json.dumps(
            {"version": 1, "station_ids": list(station_ids)},
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        self._storage.put(self.CACHE_KEY, payload)

    def _load_legacy_ids(self) -> tuple[str, ...]:
        """Read the short-lived TOML format once without deleting the source."""
        try:
            data = tomllib.loads(self._legacy_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return ()

        records = data.get("favorites", [])
        if not isinstance(records, list):
            raise ValueError("legacy favorites must be an array of tables")

        station_ids: list[str] = []
        for record in records:
            if not isinstance(record, dict):
                continue
            station_id = str(record.get("station_id") or "").strip()
            if station_id and station_id not in station_ids:
                station_ids.append(station_id)
        return tuple(station_ids)


def _decode_station_ids(payload: bytes) -> tuple[str, ...]:
    try:
        data = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("invalid streaming-radio favorites data") from error

    if not isinstance(data, dict) or data.get("version") != 1:
        raise ValueError("unsupported streaming-radio favorites version")

    raw_ids = data.get("station_ids")
    if not isinstance(raw_ids, list):
        raise ValueError("station_ids must be a list")

    station_ids: list[str] = []
    for value in raw_ids:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("station_ids must contain non-empty strings")
        normalized = value.strip()
        if normalized not in station_ids:
            station_ids.append(normalized)
    return tuple(station_ids)
