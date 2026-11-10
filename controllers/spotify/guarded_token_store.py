# SPDX-License-Identifier: MIT

"""Serialize OAuth persistence with cancellation of its owning account request."""

from collections.abc import Callable

from protocols.oauth import OAuthTokenStoreIf, OAuthTokens
from protocols.spotify.spotify_auth import SpotifyAuthError


class GuardedTokenStore(OAuthTokenStoreIf):
    def __init__(self, store: OAuthTokenStoreIf,
                 commit: Callable[[Callable[[], None]], bool]) -> None:
        self._store = store
        self._commit = commit

    def load(self) -> OAuthTokens | None:
        return self._store.load()

    def save(self, tokens: OAuthTokens) -> None:
        if not self._commit(lambda: self._store.save(tokens)):
            raise SpotifyAuthError("Spotify authorization cancelled")

    def clear(self) -> None:
        if not self._commit(self._store.clear):
            raise SpotifyAuthError("Spotify authorization cancelled")
