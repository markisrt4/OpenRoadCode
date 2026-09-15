# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for managed SDR++ preload window behavior."""

import subprocess
import unittest
from unittest.mock import call, patch

from apps.launchers.managed_sdrpp_launcher import ManagedSDRPPLauncher


class ManagedSDRPPLauncherTest(unittest.TestCase):
    @patch("apps.launchers.managed_sdrpp_launcher.subprocess.run")
    def test_preload_window_is_lowered_before_it_is_hidden(self, run) -> None:
        ManagedSDRPPLauncher._lower_and_hide(1234)

        self.assertEqual(
            [
                call(
                    ["xdotool", "windowlower", "1234"],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                ),
                call(
                    ["xdotool", "windowunmap", "1234"],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                ),
            ],
            run.call_args_list,
        )


if __name__ == "__main__":
    unittest.main()
