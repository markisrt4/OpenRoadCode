# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from security.environment_variable_secret_manager import (
    DEFAULT_SECRETS_FILE,
    EnvironmentVariableSecretManager,
    resolve_default_secrets_file,
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

    def test_default_secrets_file_is_linux_path(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            self.assertEqual(DEFAULT_SECRETS_FILE, resolve_default_secrets_file())

    def test_default_secrets_file_uses_termux_config_home(self) -> None:
        environment = {
            "PREFIX": "/data/data/com.termux/files/usr",
            "XDG_CONFIG_HOME": "/tmp/termux-config",
        }
        with patch.dict("os.environ", environment, clear=True):
            self.assertEqual(
                Path("/tmp/termux-config/openroadcode/secrets.env"),
                resolve_default_secrets_file(),
            )

    def test_secrets_file_environment_override_wins(self) -> None:
        environment = {
            "PREFIX": "/data/data/com.termux/files/usr",
            "OPENROADCODE_SECRETS_FILE": "/tmp/custom-secrets.env",
        }
        with patch.dict("os.environ", environment, clear=True):
            self.assertEqual(
                Path("/tmp/custom-secrets.env"),
                resolve_default_secrets_file(),
            )

    def test_explicit_constructor_path_still_wins(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            secrets_file = Path(directory) / "explicit.env"
            secrets_file.write_text(
                "SPOTIFY_CLIENT_ID=explicit-client-id\n",
                encoding="utf-8",
            )
            environment = {
                "PREFIX": "/data/data/com.termux/files/usr",
                "OPENROADCODE_SECRETS_FILE": "/does/not/exist",
            }
            with patch.dict("os.environ", environment, clear=True):
                manager = EnvironmentVariableSecretManager(
                    secrets_file=secrets_file,
                )

            self.assertEqual(
                "explicit-client-id",
                manager.get_secret("SPOTIFY_CLIENT_ID"),
            )


if __name__ == "__main__":
    unittest.main()
