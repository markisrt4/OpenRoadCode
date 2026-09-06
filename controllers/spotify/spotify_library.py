# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Spotify library, history, and playlist presentation types."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SpotifyLibraryTrack:
    """Immutable track metadata returned by Spotify media queries.

    @param name Track title.
    @param artist_name Display-ready artist attribution.
    @param album_name Album title when supplied by Spotify.
    @param uri Spotify track URI used for playback.
    @param album_art_url Spotify artwork URL when available.
    @param played_at ISO timestamp for history entries, when applicable.
    """

    name: str
    artist_name: str
    album_name: str | None
    uri: str
    album_art_url: str | None = None
    played_at: str | None = None


@dataclass(frozen=True, slots=True)
class SpotifyPlaylist:
    """Immutable summary of a Spotify playlist.

    @param playlist_id Spotify playlist identifier.
    @param name Playlist display name.
    @param uri Spotify playlist URI.
    @param image_url Playlist artwork URL when supplied by Spotify.
    @param item_count Number of playlist items reported by Spotify.
    @param owner_name Optional owner display name.
    """

    playlist_id: str
    name: str
    uri: str
    image_url: str | None = None
    item_count: int | None = None
    owner_name: str | None = None
