# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

from pathlib import Path

from common.xdg_paths import xdg_config_home
from protocols.auth import SecureJsonStore
from protocols.oauth import OAuthTokens, OAuthTokenStoreIf


DEFAULT_TOKEN_PATH = xdg_config_home() / "spotify" / "tokens.json"


class SpotifyTokenStore(OAuthTokenStoreIf):
    """Stores Spotify OAuth tokens using shared secure JSON persistence."""

    def __init__(self, path: Path = DEFAULT_TOKEN_PATH) -> None:
        self._store = SecureJsonStore(path)

    @property
    def path(self) -> Path:
        """Return the token-store file path."""
        return self._store.path

    def load(self) -> OAuthTokens | None:
        data = self._store.load()
        if data is None:
            return None

        refresh_token_value = data.get("refresh_token")
        scope_value = data.get("scope")

        return OAuthTokens(
            access_token=str(data["access_token"]),
            refresh_token=(
                str(refresh_token_value)
                if refresh_token_value is not None
                else None
            ),
            expires_at=float(data["expires_at"]),
            token_type=str(data.get("token_type", "Bearer")),
            scope=(
                str(scope_value)
                if scope_value is not None
                else None
            ),
        )

    def save(self, tokens: OAuthTokens) -> None:
        self._store.save(
            {
                "access_token": tokens.access_token,
                "refresh_token": tokens.refresh_token,
                "expires_at": tokens.expires_at,
                "token_type": tokens.token_type,
                "scope": tokens.scope,
            }
        )

    def clear(self) -> None:
        self._store.clear()
