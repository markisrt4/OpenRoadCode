import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from apps.carUi.runtime.spotify_runtime_factory import create_spotify_controller
from controllers.spotify import UnconfiguredController
from protocols.spotify.spotify_config import load_spotify_config


class SpotifyRuntimeFactoryTests(unittest.TestCase):
    def test_load_spotify_config_returns_none_when_file_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            missing_config = Path(tmpdir) / "config.json"
            self.assertIsNone(load_spotify_config(missing_config))

    def test_create_spotify_controller_returns_unconfigured_controller(self) -> None:
        with patch(
            "apps.carUi.runtime.spotify_runtime_factory.load_spotify_config",
            return_value=None,
        ):
            controller = create_spotify_controller()

        self.assertIsInstance(controller, UnconfiguredController)
        state = controller.current_state()
        self.assertFalse(state.is_available)
        self.assertTrue(state.configuration_required)


if __name__ == "__main__":
    unittest.main()
