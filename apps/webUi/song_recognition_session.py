# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Web adapter for frontend-neutral song recognition controllers."""
from __future__ import annotations

import os
from dataclasses import asdict

from controllers.song_recognition import (
    AcrCloudConfig,
    AcrCloudSongRecognizer,
    SongMetadataCache,
    SongRecognitionIf,
    UnconfiguredSongRecognizer,
)


class WebSongRecognitionSession:
    """Expose a song recognizer to the web frontend."""

    def __init__(
        self,
        recognizer: SongRecognitionIf | None = None,
        metadata_cache: SongMetadataCache | None = None,
    ) -> None:
        configured = recognizer is not None
        if recognizer is None:
            recognizer = self._from_environment()
            configured = recognizer is not None
        self._recognizer = recognizer or UnconfiguredSongRecognizer()
        self._configured = configured
        self._metadata_cache = metadata_cache

    @staticmethod
    def _from_environment() -> SongRecognitionIf | None:
        host = os.environ.get("ACRCLOUD_HOST", "").strip()
        key = os.environ.get("ACRCLOUD_ACCESS_KEY", "").strip()
        secret = os.environ.get("ACRCLOUD_ACCESS_SECRET", "").strip()
        if not (host and key and secret):
            return None
        return AcrCloudSongRecognizer(AcrCloudConfig(host=host, access_key=key, access_secret=secret))

    def configured(self) -> bool:
        return self._configured

    def recognize(self, audio: bytes) -> dict[str, object]:
        result = self._recognizer.recognize(audio, sample_bytes=len(audio))
        if result is None:
            return {"matched": False, "configured": self._configured}
        if self._metadata_cache is not None:
            self._metadata_cache.put_result_ids(result)
        payload = asdict(result)
        payload["artists"] = list(result.artists)
        return {"matched": True, "configured": self._configured, "song": payload}
