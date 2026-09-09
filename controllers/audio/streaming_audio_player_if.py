# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

from abc import ABC, abstractmethod


class StreamingAudioPlayerIf(ABC):
    """Interface for playing a remote audio stream."""

    @property
    @abstractmethod
    def is_playing(self) -> bool:
        """! @brief Return whether a stream is currently playing.

        @return True when a stream is playing, otherwise False.
        """

    @abstractmethod
    def play(self, stream_url: str) -> None:
        """! @brief Begin playback of a remote audio stream.

        Any currently playing stream may be replaced by the implementation.

        @param stream_url URL of the stream to begin playing.
        """

    @abstractmethod
    def stop(self) -> None:
        """! @brief Stop current stream playback, if any."""
