# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Web adapter for frontend-neutral song recognition controllers."""
from __future__ import annotations

import os
from dataclasses import asdict

from controllers.song_recognition import (
    AcrCloudConfig,
    AcrCloudSongRecognizer,
    SongRecognitionIf,
    UnconfiguredSongRecognizer,
)


class WebSongRecognitionSession:
    """Expose a song recognizer to the web frontend."""

    def __init__(self, recognizer: SongRecognitionIf | None = None) -> None:
        self._recognizer = recognizer or self._from_environment() or UnconfiguredSongRecognizer()

    @staticmethod
    def _from_environment() -> SongRecognitionIf | None:
        host = os.environ.get("ACRCLOUD_HOST", "").strip()
        key = os.environ.get("ACRCLOUD_ACCESS_KEY", "").strip()
        secret = os.environ.get("ACRCLOUD_ACCESS_SECRET", "").strip()
        if not (host and key and secret):
            return None
        return AcrCloudSongRecognizer(AcrCloudConfig(host=host, access_key=key, access_secret=secret))

    def config(self) -> dict[str, object]:
        """Return recognition-provider readiness without exposing credentials."""
        return {
            "configured": self._recognizer.is_configured,
            "provider": self._recognizer.provider_name,
        }

    def recognize(self, audio: bytes) -> dict[str, object]:
        """Recognize one encoded audio clip and normalize the web payload."""
        result = self._recognizer.recognize(audio, sample_bytes=len(audio))
        if result is None:
            return {"matched": False, **self.config()}
        payload = asdict(result)
        payload["artists"] = list(result.artists)
        return {"matched": True, **self.config(), "song": payload}
