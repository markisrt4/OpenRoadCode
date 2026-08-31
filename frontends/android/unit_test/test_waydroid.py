"""Tests for the Waydroid Android frontend."""

from __future__ import annotations

import subprocess
import unittest
from unittest.mock import patch

from frontends.android.android_app_launcher import AndroidApp, AndroidAppLauncherError
from frontends.android.waydroid import WaydroidAppLauncher


class WaydroidAppLauncherTest(unittest.TestCase):
    @patch("frontends.android.waydroid.subprocess.run")
    @patch("frontends.android.waydroid.shutil.which", return_value="/usr/bin/waydroid")
    def test_is_available_when_status_succeeds(self, _which, run) -> None:
        run.return_value = subprocess.CompletedProcess([], 0, "", "")
        self.assertTrue(WaydroidAppLauncher().is_available())

    @patch("frontends.android.waydroid.subprocess.run")
    @patch("frontends.android.waydroid.shutil.which", return_value="/usr/bin/waydroid")
    def test_list_apps_parses_waydroid_output(self, _which, run) -> None:
        run.return_value = subprocess.CompletedProcess(
            [],
            0,
            "Name: Panera\npackageName: com.panera.app\n"
            "Name: McDonald's\npackageName: com.mcdonalds.app\n",
            "",
        )
        self.assertEqual(
            WaydroidAppLauncher().list_apps(),
            (
                AndroidApp("Panera", "com.panera.app"),
                AndroidApp("McDonald's", "com.mcdonalds.app"),
            ),
        )

    @patch("frontends.android.waydroid.subprocess.run")
    @patch("frontends.android.waydroid.shutil.which", return_value="/usr/bin/waydroid")
    def test_launch_uses_package_name(self, _which, run) -> None:
        run.return_value = subprocess.CompletedProcess([], 0, "", "")
        WaydroidAppLauncher().launch("com.example.food")
        run.assert_called_once_with(
            ["waydroid", "app", "launch", "com.example.food"],
            check=False,
            capture_output=True,
            text=True,
        )

    @patch("frontends.android.waydroid.shutil.which", return_value=None)
    def test_missing_waydroid_reports_error(self, _which) -> None:
        with self.assertRaises(AndroidAppLauncherError):
            WaydroidAppLauncher().list_apps()


if __name__ == "__main__":
    unittest.main()
