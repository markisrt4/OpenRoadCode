# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Compatibility exports; shared contracts live in the independent UI package."""

from ui.media.spotify_library import (
    SpotifyLibraryTrack,
    SpotifyPlaylist,
)

__all__ = ['SpotifyLibraryTrack', 'SpotifyPlaylist']
