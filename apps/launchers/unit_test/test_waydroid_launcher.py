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
    def test_explicit_close_only_targets_the_verified_local_waydroid(self):
        launcher = WaydroidLauncher()
        with patch.object(launcher, '_run', side_effect=[
                subprocess.CompletedProcess([], 0, 'IP address: 192.168.240.112\n', ''),
                subprocess.CompletedProcess([], 0, '', '')]), patch(
                'apps.launchers.waydroid_launcher.subprocess.run', side_effect=[
                    subprocess.CompletedProcess([], 0, 'WayDroid-x86_64-Device', ''),
                    subprocess.CompletedProcess([], 0, '', '')]) as run:
            launcher.stop_app('com.waze')
        self.assertEqual(run.call_args.args[0],
            ['adb', '-s', '192.168.240.112:5555', 'shell', 'am', 'force-stop', 'com.waze'])

    def test_close_refuses_a_device_that_is_not_waydroid(self):
        launcher = WaydroidLauncher()
        with patch.object(launcher, '_run', side_effect=[
                subprocess.CompletedProcess([], 0, 'IP address: 192.168.240.112\n', ''),
                subprocess.CompletedProcess([], 0, '', '')]), patch(
                'apps.launchers.waydroid_launcher.subprocess.run', return_value=
                subprocess.CompletedProcess([], 0, 'Samsung', '')) as run:
            with self.assertRaises(WaydroidLauncherError):
                launcher.stop_app('com.waze')
        self.assertEqual(run.call_count, 1)

    @patch('apps.launchers.waydroid_launcher.subprocess.run')
    @patch('apps.launchers.waydroid_launcher.shutil.which', return_value='/usr/bin/waydroid')
    def test_destination_uses_supported_view_intent_without_a_shell(self, _which, run):
        run.return_value = subprocess.CompletedProcess([], 0, '', '')
        uri = 'waze://?ll=42.5,-83&navigate=yes'
        WaydroidLauncher().launch_uri(uri)
        self.assertEqual(run.call_args.args[0], ['waydroid', 'app', 'intent', 'android.intent.action.VIEW', uri])

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
            timeout=5,
        )

    @patch("apps.launchers.waydroid_launcher.shutil.which", return_value=None)
    def test_missing_waydroid_reports_error(self, _which) -> None:
        with self.assertRaises(WaydroidLauncherError):
            WaydroidLauncher().list_apps()


if __name__ == "__main__":
    unittest.main()
