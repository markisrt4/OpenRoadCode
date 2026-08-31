"""Tests for launching host Android intents from Termux."""
from __future__ import annotations

import subprocess
import unittest
from unittest.mock import patch

from apps.launchers.android_intent_launcher import AndroidIntentLauncher


class AndroidIntentLauncherTest(unittest.TestCase):
    @patch("apps.launchers.android_intent_launcher.subprocess.run")
    def test_open_uri_uses_android_view_intent(self, run) -> None:
        run.return_value = subprocess.CompletedProcess([], 0, "Starting: Intent", "")
        AndroidIntentLauncher("/system/bin/am").open_uri("https://example.com/order")
        run.assert_called_once_with(
            [
                "/system/bin/am",
                "start",
                "-a",
                "android.intent.action.VIEW",
                "-d",
                "https://example.com/order",
            ],
            check=False,
            capture_output=True,
            text=True,
        )

    @patch("apps.launchers.android_intent_launcher.subprocess.run")
    def test_launch_package_uses_launcher_intent(self, run) -> None:
        run.return_value = subprocess.CompletedProcess([], 0, "Starting: Intent", "")
        AndroidIntentLauncher("/system/bin/am").launch_package("com.example.food")
        args = run.call_args.args[0]
        self.assertEqual(args[0], "/system/bin/am")
        self.assertIn("com.example.food", args)


if __name__ == "__main__":
    unittest.main()
