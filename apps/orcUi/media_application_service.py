# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Application-level ownership for ORC media services.

This module owns the lifecycle of media services shared by ORC screens while
portable Spotify behavior lives below the application package.
"""

from __future__ import annotations

from apps.orcUi.adapters.spotify_local_player_factory import create_spotify_local_player
from controllers.spotify.spotify_controller_if import SpotifyControllerIf
from controllers.spotify.spotify_local_player import SpotifyLocalPlayer
from controllers.spotify.spotify_state_service import SpotifyStateService


class MediaApplicationService:
    """Own long-lived media services shared by ORC UI screens."""

    def __init__(self, spotify_controller: SpotifyControllerIf) -> None:
        self._spotify = SpotifyStateService(spotify_controller)
        self._spotify_local_player = create_spotify_local_player(self._spotify)
        self._started = False

    @property
    def spotify(self) -> SpotifyStateService:
        """Return the shared Spotify state/control service."""
        return self._spotify

    @property
    def spotify_local_player(self) -> SpotifyLocalPlayer:
        """Return the shared local Spotify Connect player lifecycle."""
        return self._spotify_local_player

    def start(self) -> None:
        """Start background media services once."""
        if self._started:
            return
        self._started = True
        self._spotify.start()

    def close(self) -> None:
        """Stop all media-owned background activity and browser playback."""
        self._spotify_local_player.close()
        self._spotify.close()
        self._started = False
