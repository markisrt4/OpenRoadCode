# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from abc import ABC, abstractmethod

from .music_video_types import MusicVideo, MusicVideoQuery


class MusicVideoIf(ABC):
    """Search for and present music videos."""

    @abstractmethod
    def find_video(
        self,
        query: MusicVideoQuery,
    ) -> MusicVideo | None:
        """Find the best matching music video.

        @param query Track metadata used to search for a video.
        @return Best matching video, or `None` when no match is available.
        """

    @abstractmethod
    def play_video(
        self,
        video: MusicVideo,
        position_ms: int = 0,
    ) -> bool:
        """Present the selected music video.

        @param video Video selected for presentation.
        @param position_ms Initial playback position in milliseconds.
        @return `True` when video playback was started.
        """

    @abstractmethod
    def stop_video(self) -> None:
        """Stop the active video presentation."""

    @abstractmethod
    def is_video_active(self) -> bool:
        """Return whether video presentation is active.

        @return `True` while a video presentation is active.
        """
