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
        """! @brief Return the latest available playback state.

        @return Latest Spotify playback state.
        """

    @abstractmethod
    def play(self) -> None:
        """Start or resume playback."""

    @abstractmethod
    def pause(self) -> None:
        """Pause playback."""

    @abstractmethod
    def play_pause(self) -> None:
        """Toggle playback."""

    @abstractmethod
    def next_track(self) -> None:
        """Skip to the next track."""

    @abstractmethod
    def previous_track(self) -> None:
        """Return to the previous track."""

    @abstractmethod
    def set_volume_percent(self, volume_percent: int) -> None:
        """! @brief Set playback volume from 0 through 100.

        @param volume_percent Requested Spotify playback volume percentage.
        """

    @abstractmethod
    def seek_to_position_ms(self, position_ms: int) -> None:
        """! @brief Seek within the current track.

        @param position_ms Target playback position in milliseconds.
        """

    @abstractmethod
    def transfer_playback(self, device_id: str, *, play: bool = True) -> None:
        """! @brief Transfer playback to a Spotify Connect device.

        @param device_id Spotify Connect device identifier that should receive playback.
        @param play Whether playback should begin immediately after transfer.
        """

    @abstractmethod
    def saved_tracks(self, *, limit: int = 20) -> tuple[SpotifyLibraryTrack, ...]:
        """! @brief Return tracks saved in the user's library.

        @param limit Maximum number of saved tracks to return.
        @return Saved Spotify library tracks.
        """

    @abstractmethod
    def recently_played(self, *, limit: int = 20) -> tuple[SpotifyLibraryTrack, ...]:
        """! @brief Return recently played tracks.

        @param limit Maximum number of history entries to return.
        @return Recently played Spotify tracks.
        """

    @abstractmethod
    def play_track(self, track_uri: str) -> None:
        """! @brief Begin playback of one Spotify track URI.

        @param track_uri Spotify URI identifying the track to play.
        """

    def playlists(self, *, limit: int = 20) -> tuple[SpotifyPlaylist, ...]:
        """! @brief Return the current user's playlists.

        Controllers without library browsing support may return an empty tuple.

        @param limit Maximum number of playlists to return.
        @return Available Spotify playlists, or an empty tuple when unsupported.
        """
        return ()

    def playlist_tracks(
        self,
        playlist_id: str,
        *,
        limit: int = 20,
    ) -> tuple[SpotifyLibraryTrack, ...]:
        """! @brief Return playable tracks from one playlist.

        Controllers without playlist browsing support may return an empty tuple.

        @param playlist_id Spotify identifier of the playlist to inspect.
        @param limit Maximum number of playlist tracks to return.
        @return Playable Spotify tracks, or an empty tuple when unsupported.
        """
        return ()
