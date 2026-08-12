# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import secrets
import webbrowser

from protocols.oauth import (
    OAuthRedirectServer,
    OAuthClient,
    OAuthError,
    OAuthTokenStoreIf,
    OAuthTokens,
    create_pkce_pair,
)
from protocols.spotify.spotify_config import (
    SpotifyConfig,
)


class SpotifyAuthError(RuntimeError):
    """
    Raised when Spotify authorization fails.
    """


class SpotifyAuth:
    """
    Provides Spotify authorization using OAuth 2.0 with PKCE.
    """

    def __init__(
        self,
        config: SpotifyConfig,
        token_store: OAuthTokenStoreIf,
        *,
        callback_timeout_seconds: float = 120.0,
        open_browser: bool = True,
    ) -> None:
        if callback_timeout_seconds <= 0:
            raise ValueError(
                "callback_timeout_seconds must be greater than zero"
            )

        self._config = config
        self._token_store = token_store
        self._callback_timeout_seconds = (
            callback_timeout_seconds
        )
        self._open_browser = open_browser

        self._oauth_client = OAuthClient(
            config.create_oauth_config()
        )

    def get_access_token(self) -> str:
        """
        Return a valid Spotify access token.

        Existing stored tokens are reused when possible.
        """
        tokens = self._token_store.load()

        if tokens is None:
            tokens = self.login()

        elif tokens.is_expired():
            if tokens.refresh_token is None:
                tokens = self.login()
            else:
                tokens = self.refresh(
                    tokens.refresh_token
                )

        return tokens.access_token

    def login(self) -> OAuthTokens:
        """
        Run the Spotify OAuth authorization flow.
        """
        pkce = create_pkce_pair()
        state = secrets.token_urlsafe(32)

        authorization_url = (
            self._oauth_client.build_authorization_url(
                state=state,
                code_challenge=pkce.challenge,
            )
        )

        print("Opening Spotify authorization URL...")
        print(authorization_url)

        if self._open_browser:
            webbrowser.open(authorization_url)

        callback_server = OAuthRedirectServer(
            self._config.redirect_uri,
            timeout_seconds=(
                self._callback_timeout_seconds
            ),
        )

        callback = (
            callback_server.wait_for_callback()
        )

        if callback.error is not None:
            message = callback.error

            if callback.error_description:
                message = (
                    f"{message}: "
                    f"{callback.error_description}"
                )

            raise SpotifyAuthError(message)

        if callback.code is None:
            raise SpotifyAuthError(
                "Spotify authorization callback "
                "did not include a code"
            )

        if callback.state != state:
            raise SpotifyAuthError(
                "Spotify authorization state did not match"
            )

        try:
            tokens = (
                self._oauth_client
                .exchange_authorization_code(
                    code=callback.code,
                    code_verifier=pkce.verifier,
                )
            )
        except OAuthError as exc:
            raise SpotifyAuthError(
                f"Spotify token exchange failed: {exc}"
            ) from exc

        self._token_store.save(tokens)

        return tokens

    def refresh(
        self,
        refresh_token: str,
    ) -> OAuthTokens:
        """
        Refresh a Spotify access token.
        """
        try:
            tokens = (
                self._oauth_client
                .refresh_access_token(
                    refresh_token
                )
            )
        except OAuthError as exc:
            raise SpotifyAuthError(
                f"Spotify token refresh failed: {exc}"
            ) from exc

        self._token_store.save(tokens)

        return tokens
