# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Spotify library and history presentation types."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SpotifyLibraryTrack:
    """Immutable track metadata returned by Spotify library/history queries."""

    name: str
    artist_name: str
    album_name: str | None
    uri: str
    album_art_url: str | None = None
    played_at: str | None = None
