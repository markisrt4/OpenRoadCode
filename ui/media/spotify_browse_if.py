# SPDX-License-Identifier: MIT

"""Toolkit-independent Spotify library and destination contracts."""

from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from ui.media.spotify_library import SpotifyLibraryTrack, SpotifyPlaylist


class SpotifyPlaybackMode(str, Enum):
    REMOTE = "REMOTE"
    PLAYER = "PLAYER"


@dataclass(frozen=True, slots=True)
class SpotifyLocalPlayerState:
    mode: SpotifyPlaybackMode = SpotifyPlaybackMode.REMOTE
    available: bool = False
    busy: bool = False
    message: str = "Remote Spotify device control"


class SpotifyCollection(str, Enum):
    HOME = "home"
    NOW = "now"
    LIKED = "liked"
    RECENT = "recent"
    PLAYLISTS = "playlists"
    PLAYLIST = "playlist"


@dataclass(frozen=True, slots=True)
class SpotifyBrowseState:
    collection: SpotifyCollection = SpotifyCollection.NOW
    title: str = ""
    tracks: tuple[SpotifyLibraryTrack, ...] = ()
    playlists: tuple[SpotifyPlaylist, ...] = ()
    player: SpotifyLocalPlayerState = SpotifyLocalPlayerState()
    loading: bool = False
    message: str = ""


class SpotifyBrowseRequests(Protocol):
    def request_collection(self, collection: SpotifyCollection) -> None:
        """! @brief Choose a library collection.

        @param collection Collection to display.
        """
        ...

    def request_playlist(self, playlist_id: str) -> None:
        """! @brief Open a displayed playlist.

        @param playlist_id Identifier from presentation state.
        """
        ...

    def request_play_track(self, uri: str) -> None:
        """! @brief Play a displayed track.

        @param uri Track URI from presentation state.
        """
        ...

    def request_playback_mode(self, mode: SpotifyPlaybackMode) -> None:
        """! @brief Choose remote or local playback.

        @param mode Requested playback destination.
        """
        ...


class SpotifyBrowseUi(Protocol):
    def set_browse_request_handler(self, handler: SpotifyBrowseRequests | None) -> None:
        """! @brief Bind or retire library requests.

        @param handler Request handler or None.
        """
        ...

    def set_browse_state(self, state: SpotifyBrowseState) -> None:
        """! @brief Render immutable library and destination state.

        @param state Library presentation snapshot.
        """
        ...

    def set_browse_artwork(self, uri: str, payload: bytes | None) -> None:
        """! @brief Render encoded artwork for displayed cards.

        @param uri Artwork URI identifying cards.
        @param payload Encoded bytes, or None on load failure.
        """
        ...


class SpotifyBrowseSession(Protocol):
    def activate(self, view: SpotifyBrowseUi) -> None:
        """! @brief Bind one visible library view.

        @param view Library presentation to bind.
        """
        ...

    def deactivate(self) -> None:
        """Retire requests and pending library deliveries."""
        ...

    def close(self) -> None:
        """Permanently retire this session."""
        ...
