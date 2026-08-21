# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""No-op song recognizer used when no provider is configured."""
from __future__ import annotations

from .song_recognition_if import SongRecognitionIf, SongRecognitionResult


class UnconfiguredSongRecognizer(SongRecognitionIf):
    """Concrete recognizer that intentionally never returns a match."""

    def recognize(
        self,
        audio: bytes,
        *,
        sample_bytes: int | None = None,
    ) -> SongRecognitionResult | None:
        del audio, sample_bytes
        return None
