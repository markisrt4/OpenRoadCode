# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for native map renderer launcher selection."""

import os
import unittest
from pathlib import Path
from unittest.mock import patch

from apps.launchers.map_renderer_launcher import _default_command


class MapRendererLauncherCommandTest(unittest.TestCase):
    @patch.dict(os.environ, {"OPENROADCODE_MAP_RENDERER_COMMAND": "/tmp/custom-renderer --flag"}, clear=True)
    def test_explicit_command_override_wins(self) -> None:
        self.assertEqual(_default_command(), ["/tmp/custom-renderer", "--flag"])

    @patch.dict(os.environ, {"PREFIX": "/data/data/com.termux/files/usr"}, clear=True)
    def test_termux_uses_termux_launcher(self) -> None:
        command = _default_command()

        self.assertEqual(command[0], "bash")
        self.assertTrue(command[1].endswith("development/termux/start_map_renderer.sh"))

    @patch.dict(os.environ, {}, clear=True)
    def test_native_linux_uses_runtime_launcher(self) -> None:
        command = _default_command()

        self.assertEqual(command[0], "bash")
        self.assertTrue(command[1].endswith("scripts/runtime/start_map_renderer.sh"))
        self.assertTrue(Path(command[1]).is_file())


if __name__ == "__main__":
    unittest.main()
