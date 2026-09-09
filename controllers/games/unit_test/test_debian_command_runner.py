# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for Debian graphical launch policy in Termux/proot."""

import unittest
from unittest.mock import patch

from controllers.games.debian_command_runner import DebianCommandRunner


class DebianCommandRunnerGraphicsTest(unittest.TestCase):
    def _proot_runner(self) -> DebianCommandRunner:
        runner = DebianCommandRunner.__new__(DebianCommandRunner)
        runner._mode = "proot"
        return runner

    @patch.dict("controllers.games.debian_command_runner.os.environ", {"DISPLAY": ":7"}, clear=False)
    @patch.object(DebianCommandRunner, "_ensure_virgl_server", return_value=False)
    def test_auto_does_not_assume_accelerated_bridge(self, ensure_virgl) -> None:
        runner = self._proot_runner()

        command = runner.graphical_command(["game"], rendering="auto")

        ensure_virgl.assert_called_once_with()
        self.assertIn("DISPLAY=:7", command)
        self.assertNotIn("GALLIUM_DRIVER=virpipe", command)
        self.assertNotIn("GALLIUM_DRIVER=llvmpipe", command)

    @patch.dict("controllers.games.debian_command_runner.os.environ", {"DISPLAY": ":7"}, clear=False)
    @patch.object(DebianCommandRunner, "_ensure_virgl_server", return_value=True)
    def test_auto_uses_virpipe_only_when_bridge_is_available(self, ensure_virgl) -> None:
        runner = self._proot_runner()

        command = runner.graphical_command(["game"], rendering="auto")

        ensure_virgl.assert_called_once_with()
        self.assertIn("GALLIUM_DRIVER=virpipe", command)

    @patch.dict("controllers.games.debian_command_runner.os.environ", {"DISPLAY": ":7"}, clear=False)
    @patch.object(DebianCommandRunner, "_ensure_virgl_server")
    def test_software_policy_uses_llvmpipe_without_probing_virgl(self, ensure_virgl) -> None:
        runner = self._proot_runner()

        command = runner.graphical_command(["game"], rendering="software")

        ensure_virgl.assert_not_called()
        self.assertIn("GALLIUM_DRIVER=llvmpipe", command)
        self.assertNotIn("GALLIUM_DRIVER=virpipe", command)

    def test_unknown_rendering_policy_is_rejected(self) -> None:
        runner = self._proot_runner()
        with self.assertRaisesRegex(ValueError, "unsupported rendering policy"):
            runner.graphical_command(["game"], rendering="phone-specific-magic")


if __name__ == "__main__":
    unittest.main()
