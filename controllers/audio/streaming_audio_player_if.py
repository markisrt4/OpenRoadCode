# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

from abc import ABC, abstractmethod


class StreamingAudioPlayerIf(ABC):
    """Interface for playing a remote audio stream."""

    @property
    @abstractmethod
    def is_playing(self) -> bool:
        """Return whether a stream is currently playing.

        @return True when a stream is currently playing.
        """

    @abstractmethod
    def play(self, stream_url: str) -> None:
        """Begin playback of ``stream_url``.

        Any currently playing stream may be replaced by the implementation.

        @param stream_url Remote audio stream URL to play.
        """

    @abstractmethod
    def stop(self) -> None:
        """Stop current stream playback, if any."""
