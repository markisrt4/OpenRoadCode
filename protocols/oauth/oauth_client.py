from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping

from protocols.oauth.oauth_types import (
    OAuthClientConfig,
    OAuthTokens,
)


class OAuthError(RuntimeError):
    """
    Base exception for OAuth failures.
    """


class OAuthHttpError(OAuthError):
    """
    Raised when an OAuth endpoint returns an HTTP error.
    """

    def __init__(
        self,
        status_code: int,
        response_body: str,
    ) -> None:
        self.status_code = status_code
        self.response_body = response_body

        super().__init__(
            f"OAuth HTTP {status_code}: {response_body}"
        )


class OAuthClient:
    """
    OAuth 2.0 authorization and token client.
    """

    def __init__(
        self,
        config: OAuthClientConfig,
        *,
        timeout_seconds: float = 10.0,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError(
                "timeout_seconds must be greater than zero"
            )

        self._config = config
        self._timeout_seconds = timeout_seconds

    @property
    def config(self) -> OAuthClientConfig:
        """Return the OAuth client configuration.

        @return Immutable authorization/token endpoint configuration.
        """
        return self._config

    def build_authorization_url(
        self,
        *,
        state: str,
        code_challenge: str,
        extra_parameters: Mapping[str, str] | None = None,
    ) -> str:
        """
        Build an OAuth authorization URL using PKCE.
        """
        if not state:
            raise ValueError("state cannot be empty")

        if not code_challenge:
            raise ValueError(
                "code_challenge cannot be empty"
            )

        parameters = {
            "client_id": self._config.client_id,
            "response_type": "code",
            "redirect_uri": self._config.redirect_uri,
            "scope": " ".join(self._config.scopes),
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }

        if extra_parameters:
            parameters.update(extra_parameters)

        return (
            f"{self._config.authorization_url}?"
            f"{urllib.parse.urlencode(parameters)}"
        )

    def exchange_authorization_code(
        self,
        *,
        code: str,
        code_verifier: str,
        extra_parameters: Mapping[str, str] | None = None,
    ) -> OAuthTokens:
        """
        Exchange an authorization code for OAuth tokens.
        """
        if not code:
            raise ValueError("code cannot be empty")

        if not code_verifier:
            raise ValueError(
                "code_verifier cannot be empty"
            )

        parameters = {
            "client_id": self._config.client_id,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self._config.redirect_uri,
            "code_verifier": code_verifier,
        }

        if extra_parameters:
            parameters.update(extra_parameters)

        response = self._post_form(parameters)

        return self._tokens_from_response(response)

    def refresh_access_token(
        self,
        refresh_token: str,
        *,
        extra_parameters: Mapping[str, str] | None = None,
    ) -> OAuthTokens:
        """
        Refresh an OAuth access token.
        """
        if not refresh_token:
            raise ValueError(
                "refresh_token cannot be empty"
            )

        parameters = {
            "client_id": self._config.client_id,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }

        if extra_parameters:
            parameters.update(extra_parameters)

        response = self._post_form(parameters)

        return self._tokens_from_response(
            response,
            existing_refresh_token=refresh_token,
        )

    def _post_form(
        self,
        parameters: Mapping[str, str],
    ) -> dict[str, object]:
        body = urllib.parse.urlencode(
            parameters
        ).encode("utf-8")

        request = urllib.request.Request(
            self._config.token_url,
            data=body,
            method="POST",
            headers={
                "Content-Type":
                    "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=self._timeout_seconds,
            ) as response:
                response_body = response.read().decode(
                    "utf-8"
                )

        except urllib.error.HTTPError as exc:
            response_body = exc.read().decode(
                "utf-8",
                errors="replace",
            )

            raise OAuthHttpError(
                exc.code,
                response_body,
            ) from exc

        except urllib.error.URLError as exc:
            raise OAuthError(
                f"Unable to reach OAuth endpoint: {exc}"
            ) from exc

        try:
            parsed = json.loads(response_body)
        except json.JSONDecodeError as exc:
            raise OAuthError(
                "OAuth endpoint returned invalid JSON"
            ) from exc

        if not isinstance(parsed, dict):
            raise OAuthError(
                "OAuth endpoint returned an invalid response"
            )

        return parsed

    @staticmethod
    def _tokens_from_response(
        response: Mapping[str, object],
        *,
        existing_refresh_token: str | None = None,
    ) -> OAuthTokens:
        access_token = response.get("access_token")

        if not isinstance(access_token, str):
            raise OAuthError(
                "OAuth response did not contain an access token"
            )

        expires_in_value = response.get(
            "expires_in",
            3600,
        )

        try:
            expires_in = int(expires_in_value)
        except (TypeError, ValueError) as exc:
            raise OAuthError(
                "OAuth response contained an invalid expiration"
            ) from exc

        refresh_token_value = response.get(
            "refresh_token"
        )

        refresh_token = (
            refresh_token_value
            if isinstance(refresh_token_value, str)
            else existing_refresh_token
        )

        token_type_value = response.get(
            "token_type",
            "Bearer",
        )

        token_type = (
            token_type_value
            if isinstance(token_type_value, str)
            else "Bearer"
        )

        scope_value = response.get("scope")

        scope = (
            scope_value
            if isinstance(scope_value, str)
            else None
        )

        return OAuthTokens(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=time.time() + expires_in,
            token_type=token_type,
            scope=scope,
        )
