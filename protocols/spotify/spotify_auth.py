# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import secrets
import webbrowser
from dataclasses import dataclass

from protocols.oauth import (
    OAuthClient,
    OAuthError,
    OAuthRedirectServer,
    OAuthTokenStoreIf,
    OAuthTokens,
    create_pkce_pair,
)
from protocols.spotify.spotify_config import SpotifyConfig


class SpotifyAuthError(RuntimeError):
    """Raised when Spotify authorization fails."""


@dataclass(frozen=True, slots=True)
class SpotifyAuthorizationRequest:
    """State required to complete one Spotify PKCE authorization flow."""

    authorization_url: str
    state: str
    code_verifier: str


class SpotifyAuth:
    """Provide Spotify OAuth 2.0 authorization using PKCE."""

    def __init__(
        self,
        config: SpotifyConfig,
        token_store: OAuthTokenStoreIf,
        *,
        callback_timeout_seconds: float = 120.0,
        open_browser: bool = True,
    ) -> None:
        if callback_timeout_seconds <= 0:
            raise ValueError("callback_timeout_seconds must be greater than zero")

        self._config = config
        self._token_store = token_store
        self._callback_timeout_seconds = callback_timeout_seconds
        self._open_browser = open_browser
        self._oauth_client = OAuthClient(config.create_oauth_config())

    @property
    def redirect_uri(self) -> str:
        """Return the configured OAuth redirect URI."""
        return self._config.redirect_uri

    def get_access_token(self) -> str:
        """Return a valid Spotify access token, authorizing when needed."""
        tokens = self._token_store.load()
        if tokens is None:
            tokens = self.login()
        elif tokens.is_expired():
            if tokens.refresh_token is None:
                tokens = self.login()
            else:
                tokens = self.refresh(tokens.refresh_token)
        return tokens.access_token

    def begin_authorization(self) -> SpotifyAuthorizationRequest:
        """Create a transport-independent Spotify authorization request."""
        pkce = create_pkce_pair()
        state = secrets.token_urlsafe(32)
        authorization_url = self._oauth_client.build_authorization_url(
            state=state,
            code_challenge=pkce.challenge,
        )
        return SpotifyAuthorizationRequest(
            authorization_url=authorization_url,
            state=state,
            code_verifier=pkce.verifier,
        )

    def complete_authorization(
        self,
        request: SpotifyAuthorizationRequest,
        *,
        code: str | None,
        state: str | None,
        error: str | None = None,
        error_description: str | None = None,
    ) -> OAuthTokens:
        """Validate an OAuth callback, exchange its code, and store tokens."""
        if error is not None:
            message = error
            if error_description:
                message = f"{message}: {error_description}"
            raise SpotifyAuthError(message)

        if code is None:
            raise SpotifyAuthError("Spotify authorization callback did not include a code")

        if state != request.state:
            raise SpotifyAuthError("Spotify authorization state did not match")

        try:
            tokens = self._oauth_client.exchange_authorization_code(
                code=code,
                code_verifier=request.code_verifier,
            )
        except OAuthError as exc:
            raise SpotifyAuthError(f"Spotify token exchange failed: {exc}") from exc

        self._token_store.save(tokens)
        return tokens

    def login(self) -> OAuthTokens:
        """Run the existing desktop-style interactive OAuth flow."""
        authorization = self.begin_authorization()

        print("Opening Spotify authorization URL...")
        print(authorization.authorization_url)
        if self._open_browser:
            webbrowser.open(authorization.authorization_url)

        callback_server = OAuthRedirectServer(
            self._config.redirect_uri,
            timeout_seconds=self._callback_timeout_seconds,
        )
        callback = callback_server.wait_for_callback()

        return self.complete_authorization(
            authorization,
            code=callback.code,
            state=callback.state,
            error=callback.error,
            error_description=callback.error_description,
        )

    def refresh(self, refresh_token: str) -> OAuthTokens:
        """Refresh and persist a Spotify access token."""
        try:
            tokens = self._oauth_client.refresh_access_token(refresh_token)
        except OAuthError as exc:
            raise SpotifyAuthError(f"Spotify token refresh failed: {exc}") from exc

        self._token_store.save(tokens)
        return tokens
