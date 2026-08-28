# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for ADS-B dashboard launch behavior."""

import unittest
from unittest.mock import Mock, patch

from apps.launchers.adsb_launcher import ADSBLauncher, _set_systemd_service_state


class AdsbLauncherTest(unittest.TestCase):
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
        which.side_effect = lambda command: {
            "systemctl": "/usr/bin/systemctl",
            "sudo": None,
        }[command]

        self.assertTrue(_set_systemd_service_state("readsb", "start"))
        subprocess_run.assert_called_once_with(
            ["/usr/bin/systemctl", "start", "readsb"],
            check=False,
        )

    @patch("apps.launchers.adsb_launcher.subprocess.run")
    @patch("apps.launchers.adsb_launcher.shutil.which")
    def test_service_control_uses_sudo_when_available(
        self,
        which: Mock,
        subprocess_run: Mock,
    ) -> None:
        which.side_effect = lambda command: {
            "systemctl": "/usr/bin/systemctl",
            "sudo": "/usr/bin/sudo",
        }[command]

        self.assertTrue(_set_systemd_service_state("readsb", "stop"))
        subprocess_run.assert_called_once_with(
            ["/usr/bin/sudo", "/usr/bin/systemctl", "stop", "readsb"],
            check=False,
        )


if __name__ == "__main__":
    unittest.main()
