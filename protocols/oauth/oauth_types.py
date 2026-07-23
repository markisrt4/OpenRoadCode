from __future__ import annotations

import time
from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping


@dataclass(frozen=True, slots=True)
class OAuthClientConfig:
    """
    Configuration for an OAuth 2.0 client.
    """

    client_id: str
    authorization_url: str
    token_url: str
    redirect_uri: str
    scopes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.client_id:
            raise ValueError("client_id cannot be empty")

        if not self.authorization_url:
            raise ValueError("authorization_url cannot be empty")

        if not self.token_url:
            raise ValueError("token_url cannot be empty")

        if not self.redirect_uri:
            raise ValueError("redirect_uri cannot be empty")


@dataclass(frozen=True, slots=True)
class OAuthTokens:
    """
    OAuth access and refresh tokens.
    """

    access_token: str
    expires_at: float
    refresh_token: str | None = None
    token_type: str = "Bearer"
    scope: str | None = None

    def __post_init__(self) -> None:
        if not self.access_token:
            raise ValueError("access_token cannot be empty")

    def is_expired(self, buffer_seconds: int = 60) -> bool:
        """
        Return whether the access token is expired or near expiration.
        """
        return time.time() >= self.expires_at - buffer_seconds


@dataclass(frozen=True, slots=True)
class OAuthCallbackResult:
    """
    Result received through an OAuth redirect callback.
    """

    code: str | None = None
    state: str | None = None
    error: str | None = None
    error_description: str | None = None
    parameters: Mapping[str, str] = MappingProxyType({})

    @property
    def is_successful(self) -> bool:
        """Return whether the callback completed successfully.

        @retval True An authorization code is present and no error was reported.
        @retval False The callback contains an error or lacks a code.
        """
        return self.code is not None and self.error is None
