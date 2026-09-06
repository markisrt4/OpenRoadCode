# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Reusable Tk media screens and panels."""

from frontends.tk.media.browser_media_screen import BrowserMediaScreen
from frontends.tk.media.media_navigation_bar import MediaNavigationBar
from frontends.tk.media.media_screen import MediaScreen
from frontends.tk.media.netflix_panel import NetflixPanel
from frontends.tk.media.spotify_playback_panel import SpotifyPlaybackPanel
from frontends.tk.media.spotify_screen import SpotifyScreen
from frontends.tk.media.youtube_panel import YouTubePanel

__all__ = [
    "BrowserMediaScreen",
    "MediaNavigationBar",
    "MediaScreen",
    "NetflixPanel",
    "SpotifyPlaybackPanel",
    "SpotifyScreen",
    "YouTubePanel",
]
