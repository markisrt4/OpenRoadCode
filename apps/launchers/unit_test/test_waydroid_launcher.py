"""Tests for the Waydroid Android application launcher."""

from __future__ import annotations

import subprocess
import unittest
from unittest.mock import patch

from apps.launchers.waydroid_launcher import (
    AndroidApp,
    WaydroidLauncher,
    WaydroidLauncherError,
)


class WaydroidLauncherTest(unittest.TestCase):
    @patch("apps.launchers.waydroid_launcher.subprocess.run")
    @patch("apps.launchers.waydroid_launcher.shutil.which", return_value="/usr/bin/waydroid")
    def test_is_available_when_status_succeeds(self, _which, run) -> None:
        run.return_value = subprocess.CompletedProcess([], 0, "", "")
        self.assertTrue(WaydroidLauncher().is_available())

    @patch("apps.launchers.waydroid_launcher.subprocess.run")
    @patch("apps.launchers.waydroid_launcher.shutil.which", return_value="/usr/bin/waydroid")
    def test_list_apps_parses_waydroid_output(self, _which, run) -> None:
        run.return_value = subprocess.CompletedProcess(
            [],
            0,
            "Name: Panera\npackageName: com.panera.app\n"
            "Name: McDonald's\npackageName: com.mcdonalds.app\n",
            "",
        )
        self.assertEqual(
            WaydroidLauncher().list_apps(),
            (
                AndroidApp("Panera", "com.panera.app"),
                AndroidApp("McDonald's", "com.mcdonalds.app"),
            ),
        )

    @patch("apps.launchers.waydroid_launcher.subprocess.run")
    @patch("apps.launchers.waydroid_launcher.shutil.which", return_value="/usr/bin/waydroid")
    def test_launch_app_uses_package_name(self, _which, run) -> None:
        run.return_value = subprocess.CompletedProcess([], 0, "", "")
        WaydroidLauncher().launch_app("com.example.food")
        run.assert_called_once_with(
            ["waydroid", "app", "launch", "com.example.food"],
            check=False,
            capture_output=True,
            text=True,
        )

    @patch("apps.launchers.waydroid_launcher.shutil.which", return_value=None)
    def test_missing_waydroid_reports_error(self, _which) -> None:
        with self.assertRaises(WaydroidLauncherError):
            WaydroidLauncher().list_apps()


if __name__ == "__main__":
    unittest.main()
