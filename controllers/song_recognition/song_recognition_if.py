# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Frontend-neutral interface for identifying recorded music."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass(frozen=True)
class SongRecognitionResult:
    """Normalized metadata returned by a song recognition provider."""

    title: str
    artists: tuple[str, ...] = field(default_factory=tuple)
    album: str | None = None
    release_date: str | None = None
    label: str | None = None
    isrc: str | None = None
    score: int | None = None
    provider: str = ""
    provider_track_id: str | None = None
    artwork_url: str | None = None
    spotify_track_id: str | None = None
    spotify_uri: str | None = None
    spotify_url: str | None = None


class SongRecognitionIf(ABC):
    """Recognize a short encoded audio sample and return normalized metadata."""

    @property
    @abstractmethod
    def is_configured(self) -> bool:
        """Return whether this recognizer is ready to make requests.

        @return True when required provider credentials are available.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def provider_name(self) -> str | None:
        """Return a human-readable provider name, if configured.

        @return Provider label or None when unconfigured.
        """
        raise NotImplementedError

    @abstractmethod
    def recognize(self, audio: bytes, *, sample_bytes: int | None = None) -> SongRecognitionResult | None:
        """Return the best matching song, or ``None`` when no match is found.

        @param audio Encoded audio sample accepted by the provider.
        @param sample_bytes Exact uploaded sample size when already known.
        @return Normalized song metadata or None when unmatched.
        """
        raise NotImplementedError
