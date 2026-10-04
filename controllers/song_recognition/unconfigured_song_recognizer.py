# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""No-op recognizer used when no song provider is configured."""
from __future__ import annotations

from .song_recognition_if import SongRecognitionIf, SongRecognitionResult


class UnconfiguredSongRecognizer(SongRecognitionIf):
    """Recognizer that intentionally never returns a match."""

    @property
    def is_configured(self) -> bool:
        return False

    @property
    def provider_name(self) -> str | None:
        return None

    def recognize(self, audio: bytes, *, sample_bytes: int | None = None) -> SongRecognitionResult | None:
        del audio, sample_bytes
        return None
