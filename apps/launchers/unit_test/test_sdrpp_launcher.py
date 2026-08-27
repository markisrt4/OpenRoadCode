# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for SDR++ launcher lifecycle behavior."""

import os
import unittest
from unittest.mock import Mock, patch

from apps.launchers.sdrpp_launcher import (
    SDRPPLauncher,
    SDRPPProfile,
    _sdrpp_environment,
    _stop_readsb_service,
)


class SDRPPLauncherTest(unittest.TestCase):
    def setUp(self) -> None:
        self.profile = SDRPPProfile(
            name="fm",
            mode="WFM",
            step_hz=100_000,
            start_frequency_hz=101_100_000,
        )

    def test_environment_targets_requested_x11_display(self) -> None:
        with patch.dict(os.environ, {"KEEP_ME": "yes"}, clear=True):
            environment = _sdrpp_environment(":1")

        self.assertEqual(":1", environment["DISPLAY"])
        self.assertEqual("x11", environment["XDG_SESSION_TYPE"])
        self.assertEqual("x11", environment["GDK_BACKEND"])
        self.assertEqual("1", environment["LIBGL_ALWAYS_SOFTWARE"])
        self.assertEqual("yes", environment["KEEP_ME"])

    @patch("apps.launchers.sdrpp_launcher.shutil.which", return_value=None)
    @patch("apps.launchers.sdrpp_launcher.subprocess.run")
    def test_readsb_stop_is_skipped_without_systemctl(
        self, run: Mock, _which: Mock
    ) -> None:
        self.assertFalse(_stop_readsb_service())
        run.assert_not_called()

    @patch("apps.launchers.sdrpp_launcher.subprocess.run")
    @patch("apps.launchers.sdrpp_launcher.shutil.which")
    def test_readsb_stop_uses_systemctl_without_sudo(
        self, which: Mock, run: Mock
    ) -> None:
        which.side_effect = lambda command: (
            "/usr/bin/systemctl" if command == "systemctl" else None
        )

        self.assertTrue(_stop_readsb_service())
        run.assert_called_once_with(
            ["/usr/bin/systemctl", "stop", "readsb"], check=False
        )

    @patch("apps.launchers.sdrpp_launcher.subprocess.run")
    @patch("apps.launchers.sdrpp_launcher.shutil.which")
    def test_readsb_stop_uses_sudo_when_available(
        self, which: Mock, run: Mock
    ) -> None:
        paths = {
            "systemctl": "/usr/bin/systemctl",
            "sudo": "/usr/bin/sudo",
        }
        which.side_effect = paths.get

        self.assertTrue(_stop_readsb_service())
        run.assert_called_once_with(
            ["/usr/bin/sudo", "/usr/bin/systemctl", "stop", "readsb"],
            check=False,
        )

    @patch("apps.launchers.sdrpp_launcher._stop_readsb_service")
    def test_existing_ready_process_does_not_spawn_another(
        self, stop_readsb: Mock
    ) -> None:
        launcher = SDRPPLauncher(profile=self.profile)
        launcher.is_running = Mock(return_value=True)
        launcher.is_rigctl_ready = Mock(return_value=True)
        launcher.wait_for_rigctl = Mock()
        status = Mock()

        with patch("apps.launchers.sdrpp_launcher.subprocess.Popen") as popen:
            launcher.launch(":1", status)

        stop_readsb.assert_called_once_with()
        popen.assert_not_called()
        launcher.wait_for_rigctl.assert_not_called()
        status.assert_called_with("SDR++ already ready: fm")

    @patch("apps.launchers.sdrpp_launcher._stop_readsb_service")
    def test_existing_process_waits_for_rigctl(self, _stop_readsb: Mock) -> None:
        launcher = SDRPPLauncher(profile=self.profile)
        launcher.is_running = Mock(return_value=True)
        launcher.is_rigctl_ready = Mock(return_value=False)
        launcher.wait_for_rigctl = Mock()

        launcher.launch(":1")

        launcher.wait_for_rigctl.assert_called_once_with()

    @patch("apps.launchers.sdrpp_launcher.shutil.which", return_value=None)
    @patch("apps.launchers.sdrpp_launcher._stop_readsb_service")
    def test_missing_executable_raises(
        self, _stop_readsb: Mock, _which: Mock
    ) -> None:
        launcher = SDRPPLauncher(profile=self.profile)
        launcher.is_running = Mock(return_value=False)

        with self.assertRaisesRegex(RuntimeError, "Could not find sdrpp"):
            launcher.launch(":1")

    @patch("apps.launchers.sdrpp_launcher.close_matching_display_apps")
    @patch("apps.launchers.sdrpp_launcher.terminate_process")
    def test_stop_terminates_owned_process_and_closes_display_apps(
        self, terminate: Mock, close_apps: Mock
    ) -> None:
        launcher = SDRPPLauncher(profile=self.profile)
        process = Mock()
        launcher._process = process
        status = Mock()

        launcher.stop(":1", status)

        terminate.assert_called_once_with(process)
        close_apps.assert_called_once_with(
            display=":1", patterns=("sdrpp", "sdr\\+\\+")
        )
        self.assertIsNone(launcher._process)
        status.assert_called_once_with("SDR++ stopped")

    @patch("apps.launchers.sdrpp_launcher._stop_readsb_service")
    def test_resource_manager_is_acquired_before_launch(
        self, _stop_readsb: Mock
    ) -> None:
        resource_manager = Mock()
        launcher = SDRPPLauncher(
            profile=self.profile,
            resource_manager=resource_manager,
            owner_name="radio-fm",
        )
        launcher.is_running = Mock(return_value=True)
        launcher.is_rigctl_ready = Mock(return_value=True)
        status = Mock()

        launcher.launch(":1", status)

        resource_manager.acquire.assert_called_once_with(
            "radio-fm", force=True, set_status=status
        )


if __name__ == "__main__":
    unittest.main()
