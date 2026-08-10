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
    load_spotify_config_from_secrets,
)
from security.environment_variable_secret_manager import (
    EnvironmentVariableSecretManager,
)
from security.secret_manager_if import SecretManagerIf


def create_spotify_controller(
    secret_manager: SecretManagerIf | None = None,
) -> SpotifyControllerIf:
    """Assemble the Spotify controller used by the Car UI."""

    resolved_secret_manager = (
        secret_manager
        if secret_manager is not None
        else EnvironmentVariableSecretManager()
    )
    config = load_spotify_config_from_secrets(resolved_secret_manager)
    if config is None:
        return UnconfiguredController()

    token_store = SpotifyTokenStore()
    auth = SpotifyAuth(
        config=config,
        token_store=token_store,
    )
    client = SpotifyWebApiClient(auth)

    return SpotifyWebApiController(client)
