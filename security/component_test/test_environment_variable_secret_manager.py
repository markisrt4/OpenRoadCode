from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from security.environment_variable_secret_manager import (
    EnvironmentVariableSecretManager,
)


class EnvironmentVariableSecretManagerTest(unittest.TestCase):
    def test_loads_environment_style_secrets_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            secrets_file = Path(directory) / "secrets.env"
            secrets_file.write_text(
                "# OpenRoadCode secrets\n"
                "SPOTIFY_CLIENT_ID=file-client-id\n"
                "SPOTIFY_REDIRECT_URI='http://localhost/callback'\n",
                encoding="utf-8",
            )

            with patch.dict("os.environ", {}, clear=True):
                manager = EnvironmentVariableSecretManager(
                    secrets_file=secrets_file,
                )

            self.assertEqual(
                "file-client-id",
                manager.get_secret("SPOTIFY_CLIENT_ID"),
            )
            self.assertEqual(
                "http://localhost/callback",
                manager.get_secret("SPOTIFY_REDIRECT_URI"),
            )

    def test_process_environment_overrides_secrets_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            secrets_file = Path(directory) / "secrets.env"
            secrets_file.write_text(
                "SPOTIFY_CLIENT_ID=file-client-id\n",
                encoding="utf-8",
            )

            with patch.dict(
                "os.environ",
                {"SPOTIFY_CLIENT_ID": "environment-client-id"},
                clear=True,
            ):
                manager = EnvironmentVariableSecretManager(
                    secrets_file=secrets_file,
                )

            self.assertEqual(
                "environment-client-id",
                manager.get_secret("SPOTIFY_CLIENT_ID"),
            )


if __name__ == "__main__":
    unittest.main()
