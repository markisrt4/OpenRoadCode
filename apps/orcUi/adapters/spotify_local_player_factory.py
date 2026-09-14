# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Compose host-specific adapters for the controller-owned Spotify local player."""

from __future__ import annotations

from apps.launchers import BrowserKioskLauncher
from apps.orcUi.adapters.spotify_web_player_host import SpotifyWebPlayerHost
from common.xdg_paths import openroadcode_data_dir
from controllers.spotify.spotify_local_player import SpotifyLocalPlayer
from controllers.spotify.spotify_state_service import SpotifyStateService

WINDOW_CLASS = "OpenRoadCodeSpotifyPlayer"
SPOTIFY_PLAYER_BROWSERS = ("google-chrome-stable", "google-chrome")


def create_spotify_local_player(
    spotify_service: SpotifyStateService,
) -> SpotifyLocalPlayer:
    """Create the local Spotify player with ORC host/browser adapters."""
    return SpotifyLocalPlayer(
        spotify_service=spotify_service,
        host_factory=SpotifyWebPlayerHost,
        browser_factory=_make_browser,
        browser_candidates=SPOTIFY_PLAYER_BROWSERS,
    )


def _make_browser(url: str) -> BrowserKioskLauncher:
    return BrowserKioskLauncher(
        url=url,
        process_pattern=WINDOW_CLASS,
        browser_candidates=SPOTIFY_PLAYER_BROWSERS,
        kiosk=False,
        app_mode=True,
        profile_path=openroadcode_data_dir("spotify-player-browser"),
        window_position=(8, 8),
        window_size=(420, 220),
        startup_grace_seconds=0.5,
        extra_arguments=("--autoplay-policy=no-user-gesture-required",),
        window_class=WINDOW_CLASS,
    )
