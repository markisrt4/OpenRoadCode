from __future__ import annotations

from abc import ABC, abstractmethod

from protocols.oauth.oauth_types import OAuthTokens


class OAuthTokenStoreIf(ABC):
    """
    Interface for loading and storing OAuth tokens.
    """

    @abstractmethod
    def load(self) -> OAuthTokens | None:
        """Load stored OAuth tokens.

        @return Stored tokens, or ``None`` when no token record exists.
        """

    @abstractmethod
    def save(self, tokens: OAuthTokens) -> None:
        """Store OAuth tokens.

        @param tokens Access and refresh tokens to persist.
        """

    @abstractmethod
    def clear(self) -> None:
        """
        Remove stored OAuth tokens.
        """
