# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Spotify OAuth and Web API configuration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from protocols.oauth import OAuthClientConfig
from security.secret_manager_if import SecretManagerIf


DEFAULT_REDIRECT_URI = "http://127.0.0.1:8888/callback"

SPOTIFY_AUTHORIZATION_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"

# Keep requested permissions explicit. Adding a scope requires existing users to
# authorize again before Spotify can issue a token containing that permission.
SPOTIFY_SCOPES = (
    "user-read-playback-state",
    "user-read-currently-playing",
    "user-modify-playback-state",
    "user-library-read",
    "user-read-recently-played",
    "playlist-read-private",
    "streaming",
    "user-read-email",
    "user-read-private",
)

SPOTIFY_CLIENT_ID_SECRET_NAME = "SPOTIFY_CLIENT_ID"
SPOTIFY_REDIRECT_URI_SECRET_NAME = "SPOTIFY_REDIRECT_URI"


@dataclass(frozen=True, slots=True)
class SpotifyConfig:
    """Spotify OAuth and API configuration.

    @param client_id Public Spotify application client identifier.
    @param redirect_uri OAuth PKCE callback URI registered with Spotify.
    """

    client_id: str
    redirect_uri: str = DEFAULT_REDIRECT_URI

    def __post_init__(self) -> None:
        if not self.client_id:
            raise ValueError("client_id cannot be empty")
        if not self.redirect_uri:
            raise ValueError("redirect_uri cannot be empty")

    def create_oauth_config(self) -> OAuthClientConfig:
        """Create the generic OAuth configuration used by Spotify.

        @return OAuth configuration containing the Spotify endpoints and scopes.
        """
        return OAuthClientConfig(
            client_id=self.client_id,
            authorization_url=SPOTIFY_AUTHORIZATION_URL,
            token_url=SPOTIFY_TOKEN_URL,
            redirect_uri=self.redirect_uri,
            scopes=SPOTIFY_SCOPES,
        )


def load_spotify_config_from_secrets(
    secret_manager: SecretManagerIf,
    *,
    client_id_secret_name: str = SPOTIFY_CLIENT_ID_SECRET_NAME,
    redirect_uri_secret_name: str = SPOTIFY_REDIRECT_URI_SECRET_NAME,
) -> Optional[SpotifyConfig]:
    """Load Spotify configuration from a secret manager.

    Spotify uses OAuth PKCE, so no client secret is required.

    @param secret_manager Source of runtime secrets.
    @param client_id_secret_name Secret key containing the Spotify client ID.
    @param redirect_uri_secret_name Optional secret key overriding the callback.
    @return Configured Spotify settings, or ``None`` when no client ID exists.
    """
    client_id = secret_manager.get_secret(client_id_secret_name)
    if client_id is None:
        return None

    redirect_uri = secret_manager.get_secret(redirect_uri_secret_name) or DEFAULT_REDIRECT_URI
    return SpotifyConfig(client_id=client_id, redirect_uri=redirect_uri)
