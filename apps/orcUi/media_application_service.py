# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Application-level ownership for ORC media services.

This module owns the lifecycle of media services shared by ORC screens while
portable Spotify behavior lives below the application package.
"""

from __future__ import annotations

import logging

from common.logging.structured import event
from common.resource_cleanup import ResourceCleanup

from apps.orcUi.adapters.spotify_local_player_factory import create_spotify_local_player
from controllers.spotify.spotify_controller_if import SpotifyControllerIf
from controllers.spotify.spotify_local_player import SpotifyLocalPlayer
from controllers.spotify.spotify_state_service import SpotifyStateService

LOGGER = logging.getLogger("media.lifecycle")


class MediaApplicationService:
    """Own long-lived media services shared by ORC UI screens."""

    def __init__(self, spotify_controller: SpotifyControllerIf) -> None:
        with ResourceCleanup() as cleanup:
            self._spotify = SpotifyStateService(spotify_controller)
            cleanup.callback(self._spotify.close)
            self._spotify_local_player = create_spotify_local_player(self._spotify)
            cleanup.release()
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
        try:
            self._spotify.start()
        except Exception as error:
            event(
                LOGGER,
                logging.ERROR,
                "media.start_failed",
                "Media services failed to start",
                exception_type=type(error).__name__,
            )
            raise
        self._started = True
        event(LOGGER, logging.INFO, "media.started", "Media services started")

    def close(self) -> None:
        """Stop all media-owned background activity and browser playback."""
        started = self._started
        try:
            try:
                self._spotify_local_player.close()
            finally:
                self._spotify.close()
        except Exception as error:
            event(
                LOGGER,
                logging.ERROR,
                "media.close_failed",
                "Media service shutdown failed",
                exception_type=type(error).__name__,
            )
            raise
        finally:
            self._started = False
        if started:
            event(LOGGER, logging.INFO, "media.stopped", "Media services stopped")
