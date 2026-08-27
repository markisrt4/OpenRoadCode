# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

import unittest
from unittest.mock import patch

from apps.carUi.runtime.spotify_runtime_factory import create_spotify_controller
from controllers.spotify import UnconfiguredController
from protocols.spotify.spotify_config import load_spotify_config_from_secrets


class SecretManagerStub:
    def __init__(self, values: dict[str, str] | None = None) -> None:
        self._values = values or {}

    def get_secret(self, name: str) -> str | None:
        return self._values.get(name)


class SpotifyRuntimeFactoryTests(unittest.TestCase):
    def test_load_spotify_config_returns_none_when_secret_missing(self) -> None:
        self.assertIsNone(
            load_spotify_config_from_secrets(SecretManagerStub())
        )

    def test_create_spotify_controller_returns_unconfigured_controller(self) -> None:
        with patch(
            "apps.common.spotify_controller_factory."
            "load_spotify_config_from_secrets",
            return_value=None,
        ):
            controller = create_spotify_controller()

        self.assertIsInstance(controller, UnconfiguredController)
        state = controller.current_state()
        self.assertFalse(state.is_available)
        self.assertTrue(state.configuration_required)


if __name__ == "__main__":
    unittest.main()
