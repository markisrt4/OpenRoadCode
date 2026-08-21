# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Web adapter for frontend-neutral song recognition controllers."""
from __future__ import annotations

import os
from dataclasses import asdict

from controllers.song_recognition import AcrCloudConfig, AcrCloudSongRecognizer, SongRecognitionIf


class WebSongRecognitionSession:
    """Own the configured recognizer and expose JSON-friendly results to Flask."""

    def __init__(self, recognizer: SongRecognitionIf | None = None) -> None:
        self._recognizer = recognizer or self._from_environment()

    @staticmethod
    def _from_environment() -> SongRecognitionIf | None:
        host = os.environ.get("ACRCLOUD_HOST", "").strip()
        key = os.environ.get("ACRCLOUD_ACCESS_KEY", "").strip()
        secret = os.environ.get("ACRCLOUD_ACCESS_SECRET", "").strip()
        if not (host and key and secret):
            return None
        return AcrCloudSongRecognizer(AcrCloudConfig(host=host, access_key=key, access_secret=secret))

    def configured(self) -> bool:
        return self._recognizer is not None

    def recognize(self, audio: bytes) -> dict[str, object]:
        if self._recognizer is None:
            raise RuntimeError("Song recognition is not configured. Set ACRCLOUD_HOST, ACRCLOUD_ACCESS_KEY, and ACRCLOUD_ACCESS_SECRET.")
        result = self._recognizer.recognize(audio, sample_bytes=len(audio))
        if result is None:
            return {"matched": False}
        payload = asdict(result)
        payload["artists"] = list(result.artists)
        return {"matched": True, "song": payload}
