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
        """Return the latest available playback state.

        @return Latest known Spotify playback state.
        """

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
    def set_volume_percent(self, volume_percent: int) -> None:
        """Set playback volume from 0 through 100.

        @param volume_percent Requested playback volume percentage.
        """

    @abstractmethod
    def seek_to_position_ms(self, position_ms: int) -> None:
        """Seek within the current track.

        @param position_ms Target playback position in milliseconds.
        """

    @abstractmethod
    def transfer_playback(self, device_id: str, *, play: bool = True) -> None:
        """Transfer playback to a Spotify Connect device.

        @param device_id Spotify Connect destination device identifier.
        @param play Whether playback should start or continue after transfer.
        """

    @abstractmethod
    def saved_tracks(self, *, limit: int = 20) -> tuple[SpotifyLibraryTrack, ...]:
        """Return tracks saved in the user's library.

        @param limit Maximum number of tracks to return.
        @return Saved tracks returned by Spotify.
        """

    @abstractmethod
    def recently_played(self, *, limit: int = 20) -> tuple[SpotifyLibraryTrack, ...]:
        """Return recently played tracks.

        @param limit Maximum number of tracks to return.
        @return Recently played tracks returned by Spotify.
        """

    @abstractmethod
    def play_track(self, track_uri: str) -> None:
        """Begin playback of one Spotify track URI.

        @param track_uri Spotify track URI to play.
        """

    def playlists(self, *, limit: int = 20) -> tuple[SpotifyPlaylist, ...]:
        """Return the current user's playlists.

        Controllers without library browsing support may return an empty tuple.

        @param limit Maximum number of playlists to return.
        @return Available playlists, or an empty tuple when unsupported.
        """
        return ()

    def playlist_tracks(self, playlist_id: str, *, limit: int = 20) -> tuple[SpotifyLibraryTrack, ...]:
        """Return playable tracks from one playlist.

        Controllers without playlist browsing support may return an empty tuple.

        @param playlist_id Spotify playlist identifier to inspect.
        @param limit Maximum number of tracks to return.
        @return Playable tracks in the playlist, or an empty tuple when unsupported.
        """
        return ()
