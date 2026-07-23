from abc import ABC, abstractmethod

from .music_video_types import MusicVideo, MusicVideoQuery


class MusicVideoIf(ABC):
    """Search for and present music videos."""

    @abstractmethod
    def find_video(
        self,
        query: MusicVideoQuery,
    ) -> MusicVideo | None:
        """Find the best matching music video."""

    @abstractmethod
    def play_video(
        self,
        video: MusicVideo,
        position_ms: int = 0,
    ) -> bool:
        """Present the selected music video."""

    @abstractmethod
    def stop_video(self) -> None:
        """Stop the active video presentation."""

    @abstractmethod
    def is_video_active(self) -> bool:
        """Return whether video presentation is active."""
