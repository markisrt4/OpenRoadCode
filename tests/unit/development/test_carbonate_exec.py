# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Tests for the Carbonate process launcher."""

from __future__ import annotations

import os
from unittest.mock import patch

from development.calendar.carbonate_exec import main


def test_missing_executable_argument() -> None:
    with patch("sys.argv", ["carbonate_exec.py"]):
        assert main() == 2


def test_missing_secret_does_not_launch() -> None:
    with (
        patch("sys.argv", ["carbonate_exec.py", "/bin/carbonate"]),
        patch(
            "development.calendar.carbonate_exec.EnvironmentVariableSecretManager"
        ) as manager,
    ):
        manager.return_value.require_secret.side_effect = RuntimeError("missing")
        assert main() == 1


def test_launch_passes_secret_in_environment_only() -> None:
    with (
        patch("sys.argv", ["carbonate_exec.py", "/bin/carbonate"]),
        patch(
            "development.calendar.carbonate_exec.EnvironmentVariableSecretManager"
        ) as manager,
        patch("development.calendar.carbonate_exec.os.execve") as execve,
    ):
        manager.return_value.require_secret.return_value = "test-bridge-secret"
        assert main() == 0
        executable, argv, env = execve.call_args.args
        assert executable == "/bin/carbonate"
        assert argv == ["/bin/carbonate", "serve"]
        assert env["CARBONATE_BRIDGE_PASSWORD"] == "test-bridge-secret"
        assert "test-bridge-secret" not in " ".join(argv)
