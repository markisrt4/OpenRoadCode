# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Spotify application session used by the Web frontend."""

from __future__ import annotations

from dataclasses import asdict
from threading import RLock

from apps.common.spotify_controller_factory import create_spotify_controller
from controllers.lyrics import LrclibLyricsClient
from controllers.spotify import SpotifyMediaPresenter
from protocols.spotify import (
    SpotifyAuth,
    SpotifyAuthorizationRequest,
    SpotifyTokenStore,
    SpotifyWebApiClient,
    load_spotify_config_from_secrets,
)
from security.environment_variable_secret_manager import EnvironmentVariableSecretManager
from ui.media import MediaState, MediaUiStub


class WebSpotifySession:
    """Expose shared Spotify behavior and Web OAuth state to WebUi routes."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._lyrics = LrclibLyricsClient()
        self._authorization: SpotifyAuthorizationRequest | None = None
        self._auth: SpotifyAuth | None = None
        self._configure_backend()

    def _configure_backend(self) -> None:
        self._backend = create_spotify_controller()
        self._ui = MediaUiStub()
        self._presenter = SpotifyMediaPresenter(self._backend, self._ui)

    def auth_config(self) -> dict[str, object]:
        """Return non-secret effective OAuth configuration for diagnostics."""
        config = load_spotify_config_from_secrets(EnvironmentVariableSecretManager())
        if config is None:
            return {
                "configured": False,
                "redirect_uri": None,
            }
        return {
            "configured": True,
            "redirect_uri": config.redirect_uri,
        }

    def begin_authorization(self) -> str:
        """Begin Spotify OAuth and return the external authorization URL."""
        with self._lock:
            config = load_spotify_config_from_secrets(EnvironmentVariableSecretManager())
            if config is None:
                raise RuntimeError("Spotify is not configured. Expected SPOTIFY_CLIENT_ID.")
            self._auth = SpotifyAuth(config=config, token_store=SpotifyTokenStore(), open_browser=False)
            self._authorization = self._auth.begin_authorization()
            return self._authorization.authorization_url

    def complete_authorization(
        self,
        *,
        code: str | None,
        state: str | None,
        error: str | None = None,
        error_description: str | None = None,
    ) -> None:
        """Complete the pending Web OAuth flow and rebuild the media backend."""
        with self._lock:
            if self._auth is None or self._authorization is None:
                raise RuntimeError("No Spotify authorization is pending.")
            self._auth.complete_authorization(
                self._authorization,
                code=code,
                state=state,
                error=error,
                error_description=error_description,
            )
            self._authorization = None
            self._auth = None
            self._configure_backend()

    def state(self) -> dict[str, object]:
        with self._lock:
            state = self._presenter.read_state()
            return self._serialize_state(state)

    def command(self, command: str, value: object | None = None) -> dict[str, object]:
        with self._lock:
            actions = {
                "play": self._presenter.request_play,
                "pause": self._presenter.request_pause,
                "previous": self._presenter.request_previous_track,
                "next": self._presenter.request_next_track,
            }
            if command in actions:
                actions[command]()
            elif command == "volume":
                self._presenter.request_volume(int(value))
            elif command == "seek":
                self._presenter.request_seek(float(value))
            else:
                raise ValueError(f"Unknown Spotify command: {command}")
            return self._serialize_state(self._presenter.read_state())

    def lyrics(self) -> dict[str, object]:
        with self._lock:
            state = self._presenter.read_state()
            if not state.title or not state.artist:
                return {"synced_lines": [], "plain_lines": []}
            result = self._lyrics.get_lyrics(
                track_name=state.title,
                artist_name=state.artist,
                album_name=state.album or "",
                duration_ms=int((state.duration_s or 0.0) * 1000.0),
            )
            if result is None:
                return {"synced_lines": [], "plain_lines": []}
            return {
                "synced_lines": [asdict(line) for line in result.synced_lines],
                "plain_lines": list(result.plain_lines),
            }

    @staticmethod
    def _serialize_state(state: MediaState) -> dict[str, object]:
        return {
            "availability": state.availability.name.lower(),
            "playback": state.playback.name.lower(),
            "title": state.title,
            "artist": state.artist,
            "album": state.album,
            "artwork_uri": state.artwork_uri,
            "media_uri": state.media_uri,
            "position_s": state.position_s,
            "duration_s": state.duration_s,
            "volume_percent": state.volume_percent,
            "device_name": state.device_name,
            "status_message": state.status_message,
        }
