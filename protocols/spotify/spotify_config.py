# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from protocols.oauth import OAuthClientConfig
from security.secret_manager_if import SecretManagerIf


DEFAULT_REDIRECT_URI = "http://127.0.0.1:8888/callback"

SPOTIFY_AUTHORIZATION_URL = (
    "https://accounts.spotify.com/authorize"
)

SPOTIFY_TOKEN_URL = (
    "https://accounts.spotify.com/api/token"
)

SPOTIFY_SCOPES = (
    "user-read-playback-state",
    "user-read-currently-playing",
    "user-modify-playback-state",
)

SPOTIFY_CLIENT_ID_SECRET_NAME = "SPOTIFY_CLIENT_ID"
SPOTIFY_REDIRECT_URI_SECRET_NAME = "SPOTIFY_REDIRECT_URI"


@dataclass(frozen=True, slots=True)
class SpotifyConfig:
    """
    Spotify OAuth and API configuration.
    """

    client_id: str
    redirect_uri: str = DEFAULT_REDIRECT_URI

    def __post_init__(self) -> None:
        if not self.client_id:
            raise ValueError("client_id cannot be empty")

        if not self.redirect_uri:
            raise ValueError("redirect_uri cannot be empty")

    def create_oauth_config(self) -> OAuthClientConfig:
        """
        Create the generic OAuth configuration used by Spotify.
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

    Returns ``None`` when the required client ID is unavailable. Spotify uses
    OAuth PKCE, so no client secret is required.
    """
    client_id = secret_manager.get_secret(client_id_secret_name)
    if client_id is None:
        return None

    redirect_uri = (
        secret_manager.get_secret(redirect_uri_secret_name)
        or DEFAULT_REDIRECT_URI
    )
    return SpotifyConfig(
        client_id=client_id,
        redirect_uri=redirect_uri,
    )
