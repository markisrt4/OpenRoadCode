# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for ADS-B dashboard launch behavior."""

import tempfile
import unittest
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

from apps.launchers.adsb_launcher import ADSBLauncher, _set_systemd_service_state


class AdsbLauncherTest(unittest.TestCase):
    def test_tar1090_theme_overrides_default_and_saved_mode(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "config.js"
            config_path.write_text(
                "//darkModeDefault = true;\n",
                encoding="utf-8",
            )
            launcher = ADSBLauncher(tar1090_config_path=config_path)
            launcher.browser = Mock()

            launcher.set_preferred_color_scheme("light")

            content = config_path.read_text(encoding="utf-8")
            self.assertIn("darkModeDefault = false;", content)
            self.assertIn("loStore.darkMode = false;", content)
            launcher.browser.set_preferred_color_scheme.assert_called_once_with(
                "light"
            )

    @patch("apps.launchers.adsb_launcher._set_systemd_service_state")
    def test_reachable_dashboard_opens_without_receiver_hardware(
        self,
        set_service_state: Mock,
    ) -> None:
        launcher = ADSBLauncher()
        launcher.browser = Mock()
        launcher._readsb_is_running = Mock(return_value=False)
        launcher._dashboard_is_reachable = Mock(return_value=True)
        launcher._wait_for_readsb = Mock()
        status = Mock()

        launcher.launch(":0", status)

        set_service_state.assert_called_once_with("readsb", "start")
        launcher._wait_for_readsb.assert_not_called()
        launcher.browser.launch.assert_called_once_with(":0", status)
        self.assertTrue(
            any(
                "without live data" in call.args[0]
                for call in status.call_args_list
            )
        )

    @patch("apps.launchers.adsb_launcher.shutil.which", return_value=None)
    @patch("apps.launchers.adsb_launcher.subprocess.run")
    def test_service_control_is_skipped_without_systemctl(
        self,
        subprocess_run: Mock,
        _which: Mock,
    ) -> None:
        self.assertFalse(_set_systemd_service_state("readsb", "start"))
        subprocess_run.assert_not_called()

    @patch("apps.launchers.adsb_launcher.subprocess.run")
    @patch("apps.launchers.adsb_launcher.shutil.which")
    def test_service_control_uses_systemctl_without_sudo(
        self,
        which: Mock,
        subprocess_run: Mock,
    ) -> None:
        which.return_value = "/usr/bin/systemctl"
        subprocess_run.side_effect = [
            Mock(returncode=0, stdout="loaded\n"),
            Mock(returncode=0),
        ]

        self.assertTrue(_set_systemd_service_state("readsb", "start"))
        self.assertEqual(subprocess_run.call_count, 2)
        subprocess_run.assert_any_call(
            ["/usr/bin/systemctl", "start", "readsb.service"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5.0,
        )

    @patch("apps.launchers.adsb_launcher.subprocess.run")
    @patch("apps.launchers.adsb_launcher.shutil.which")
    def test_service_control_rejects_missing_unit_without_sudo(
        self,
        which: Mock,
        subprocess_run: Mock,
    ) -> None:
        which.return_value = "/usr/bin/systemctl"
        subprocess_run.return_value = Mock(returncode=0, stdout="not-found\n")

        self.assertFalse(_set_systemd_service_state("readsb", "stop"))
        subprocess_run.assert_called_once_with(
            ["/usr/bin/systemctl", "show", "--property=LoadState", "--value", "readsb.service"],
            check=False,
            capture_output=True,
            text=True,
            timeout=2.0,
        )


if __name__ == "__main__":
    unittest.main()
