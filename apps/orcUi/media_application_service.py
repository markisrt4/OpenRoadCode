# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Application-level ownership for ORC media services.

This module is the composition boundary between the portable/controller media
stack and Tk presentation.  It deliberately owns long-lived Spotify state and
local-player lifecycles so individual screens do not construct backend
services or decide when they should be started and stopped.
"""

from __future__ import annotations

from apps.orcUi.spotify_local_player import SpotifyLocalPlayer
from apps.orcUi.spotify_state_service import SpotifyStateService


class MediaApplicationService:
    """Own long-lived media services shared by ORC UI screens."""

    def __init__(self) -> None:
        self._spotify = SpotifyStateService()
        self._spotify_local_player = SpotifyLocalPlayer(
            spotify_service=self._spotify,
        )
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
