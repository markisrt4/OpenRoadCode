# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Application-facing Spotify controller contract."""

from abc import ABC, abstractmethod

from controllers.spotify.spotify_library import SpotifyLibraryTrack, SpotifyPlaylist
from controllers.spotify.spotify_state import SpotifyState


class SpotifyControllerIf(ABC):
    """Playback, library, history, and playlist contract for Spotify apps."""

    @abstractmethod
    def current_state(self) -> SpotifyState:
        """Return the latest available playback state."""

    @abstractmethod
    def play(self) -> None: """Start or resume playback."""
    @abstractmethod
    def pause(self) -> None: """Pause playback."""
    @abstractmethod
    def play_pause(self) -> None: """Toggle playback."""
    @abstractmethod
    def next_track(self) -> None: """Skip to the next track."""
    @abstractmethod
    def previous_track(self) -> None: """Return to the previous track."""
    @abstractmethod
    def set_volume_percent(self, volume_percent: int) -> None: """Set playback volume from 0 through 100."""
    @abstractmethod
    def seek_to_position_ms(self, position_ms: int) -> None: """Seek within the current track."""
    @abstractmethod
    def transfer_playback(self, device_id: str, *, play: bool = True) -> None: """Transfer playback to a Spotify Connect device."""
    @abstractmethod
    def saved_tracks(self, *, limit: int = 20) -> tuple[SpotifyLibraryTrack, ...]: """Return tracks saved in the user's library."""
    @abstractmethod
    def recently_played(self, *, limit: int = 20) -> tuple[SpotifyLibraryTrack, ...]: """Return recently played tracks."""
    @abstractmethod
    def play_track(self, track_uri: str) -> None: """Begin playback of one Spotify track URI."""

    def playlists(self, *, limit: int = 20) -> tuple[SpotifyPlaylist, ...]:
        """Return the current user's playlists.

        Controllers without library browsing support may return an empty tuple.
        """
        return ()

    def playlist_tracks(self, playlist_id: str, *, limit: int = 20) -> tuple[SpotifyLibraryTrack, ...]:
        """Return playable tracks from one playlist.

        Controllers without playlist browsing support may return an empty tuple.
        """
        return ()
