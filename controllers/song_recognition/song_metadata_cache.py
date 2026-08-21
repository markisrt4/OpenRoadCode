# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Persistent provider-neutral cache for normalized song metadata."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass

from controllers.cache.persistent_cache_if import PersistentCacheIf
from .song_recognition_if import SongRecognitionResult


@dataclass(frozen=True)
class SongId:
    """A song identifier in an arbitrary namespace.

    Examples include ``isrc``, ``acrcloud``, ``musicbrainz`` and a future
    locally generated ``audio_fingerprint`` namespace.  The cache itself
    deliberately assigns no meaning to the namespace.
    """

    namespace: str
    value: str

    def cache_key(self) -> str:
        namespace = self.namespace.strip().lower()
        value = self.value.strip()
        if not namespace or not value:
            raise ValueError("SongId namespace and value must be non-empty")
        return f"song:{namespace}:{value}"


class SongMetadataCache:
    """Serialize normalized recognition results over ``PersistentCacheIf``."""

    def __init__(self, cache: PersistentCacheIf) -> None:
        self._cache = cache

    def get(self, song_id: SongId) -> SongRecognitionResult | None:
        data = self._cache.get(song_id.cache_key())
        if data is None:
            return None
        payload = json.loads(data.decode("utf-8"))
        payload["artists"] = tuple(payload.get("artists") or ())
        return SongRecognitionResult(**payload)

    def put(self, song_id: SongId, result: SongRecognitionResult) -> None:
        data = json.dumps(asdict(result), separators=(",", ":"), sort_keys=True).encode("utf-8")
        self._cache.put(song_id.cache_key(), data)

    def put_result_ids(self, result: SongRecognitionResult) -> tuple[SongId, ...]:
        """Cache a result under every stable identifier it currently exposes."""
        ids: list[SongId] = []
        if result.isrc:
            ids.append(SongId("isrc", result.isrc))
        if result.provider and result.provider_track_id:
            ids.append(SongId(result.provider, result.provider_track_id))
        for song_id in ids:
            self.put(song_id, result)
        return tuple(ids)
