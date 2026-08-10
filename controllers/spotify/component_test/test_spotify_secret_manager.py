from __future__ import annotations

import unittest

from apps.carUi.runtime.spotify_runtime_factory import (
    create_spotify_controller,
)
from controllers.spotify import SpotifyWebApiController
from protocols.spotify import (
    DEFAULT_REDIRECT_URI,
    load_spotify_config_from_secrets,
)
from security.environment_variable_secret_manager import (
    EnvironmentVariableSecretManager,
)


class SpotifySecretManagerComponentTest(unittest.TestCase):
    """Verify Spotify assembly using environment-backed secrets."""

    def test_loads_client_id_and_redirect_uri_from_secrets(self) -> None:
        secret_manager = EnvironmentVariableSecretManager(
            {
                "SPOTIFY_CLIENT_ID": " test-client-id ",
                "SPOTIFY_REDIRECT_URI": (
                    " http://localhost:9999/callback "
                ),
            }
        )

        config = load_spotify_config_from_secrets(secret_manager)

        self.assertIsNotNone(config)
        assert config is not None
        self.assertEqual("test-client-id", config.client_id)
        self.assertEqual(
            "http://localhost:9999/callback",
            config.redirect_uri,
        )

    def test_uses_default_redirect_uri_when_secret_is_missing(self) -> None:
        secret_manager = EnvironmentVariableSecretManager(
            {"SPOTIFY_CLIENT_ID": "test-client-id"}
        )

        config = load_spotify_config_from_secrets(secret_manager)

        self.assertIsNotNone(config)
        assert config is not None
        self.assertEqual(DEFAULT_REDIRECT_URI, config.redirect_uri)

    def test_returns_none_when_client_id_secret_is_missing(self) -> None:
        secret_manager = EnvironmentVariableSecretManager({})

        config = load_spotify_config_from_secrets(secret_manager)

        self.assertIsNone(config)

    def test_runtime_factory_accepts_injected_secret_manager(self) -> None:
        secret_manager = EnvironmentVariableSecretManager(
            {"SPOTIFY_CLIENT_ID": "test-client-id"}
        )

        controller = create_spotify_controller(secret_manager)

        self.assertIsInstance(controller, SpotifyWebApiController)


if __name__ == "__main__":
    unittest.main(verbosity=2)
