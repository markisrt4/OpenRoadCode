# SPDX-License-Identifier: MIT

"""Immutable account presentation and semantic setup requests."""

from dataclasses import dataclass
from enum import Enum
from typing import Protocol


class SpotifyAccountAction(str, Enum):
    NONE = "none"
    CONFIGURE = "configure"
    CONNECT = "connect"
    DISCONNECT = "disconnect"


@dataclass(frozen=True, slots=True)
class SpotifyAccountState:
    client_id: str = ""
    connected: bool = False
    online: bool = True
    loading: bool = True
    busy: bool = False
    action: SpotifyAccountAction = SpotifyAccountAction.NONE
    message: str = ""
    error: bool = False

    @property
    def configured(self) -> bool:
        """Return whether a public application client ID is configured.

        @return True when a client ID is present.
        """
        return bool(self.client_id)


class SpotifyAccountRequests(Protocol):
    def request_configure(self, client_id: str) -> None:
        """! @brief Save an application client ID.

        @param client_id Public Spotify application identifier.
        """
        ...

    def request_connect(self) -> None:
        """Authorize the Spotify account asynchronously."""
        ...

    def request_disconnect(self) -> None:
        """Clear account tokens and supersede pending authorization."""
        ...


class SpotifyAccountUi(Protocol):
    def set_spotify_account_state(self, state: SpotifyAccountState) -> None:
        """! @brief Render immutable configuration and authorization state.

        @param state Account snapshot, containing no tokens or client secrets.
        """
        ...

    def set_spotify_account_handler(self, handler: SpotifyAccountRequests | None) -> None:
        """! @brief Bind or retire account requests.

        @param handler Active handler, or None when the view retires.
        """
        ...


class SpotifyAccountSession(Protocol):
    def activate(self, view: SpotifyAccountUi) -> None:
        """! @brief Bind a visible account presentation.

        @param view Presentation receiving account state.
        """
        ...

    def deactivate(self) -> None:
        """Retire this presentation and cancel its pending action."""
        ...

    def close(self) -> None:
        """Permanently retire this presentation session."""
        ...
