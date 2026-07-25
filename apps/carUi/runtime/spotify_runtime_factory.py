from __future__ import annotations

from controllers.spotify import (
    SpotifyControllerIf,
    SpotifyWebApiController,
    UnconfiguredController,
)
from protocols.spotify import (
    SpotifyAuth,
    SpotifyTokenStore,
    SpotifyWebApiClient,
    load_spotify_config,
)


def create_spotify_controller() -> SpotifyControllerIf:
    """Assemble the Spotify controller used by the Car UI."""

    config = load_spotify_config()
    if config is None:
        return UnconfiguredController()

    token_store = SpotifyTokenStore()
    auth = SpotifyAuth(
        config=config,
        token_store=token_store,
    )
    client = SpotifyWebApiClient(auth)

    return SpotifyWebApiController(client)
