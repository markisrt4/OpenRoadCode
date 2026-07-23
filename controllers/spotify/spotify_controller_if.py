from abc import ABC, abstractmethod

from controllers.spotify.spotify_state import SpotifyState


class SpotifyControllerIf(ABC):
    """Playback-control contract used by Spotify user interfaces."""

    @abstractmethod
    def current_state(self) -> SpotifyState:
        """Return the latest available playback state.

        @return Immutable availability, device, track, and progress snapshot.
        """

    @abstractmethod
    def play_pause(self) -> None:
        """Toggle between playing and paused states."""

    @abstractmethod
    def next_track(self) -> None:
        """Skip to the next track in the active playback context."""

    @abstractmethod
    def previous_track(self) -> None:
        """Return to the previous track in the active playback context."""

    @abstractmethod
    def set_volume_percent(self, volume_percent: int) -> None:
        """Set playback volume.

        @param volume_percent Volume in the inclusive range 0 through 100.
        """

    @abstractmethod
    def seek_to_position_ms(self, position_ms: int) -> None:
        """Seek within the current track.

        @param position_ms Zero-based track position in milliseconds.
        """
