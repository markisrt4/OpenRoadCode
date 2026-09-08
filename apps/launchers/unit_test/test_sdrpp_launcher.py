# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for SDR++ launcher lifecycle behavior."""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from apps.launchers.sdrpp_launcher import (
    SDRPPLauncher,
    SDRPPProfile,
    _is_termux,
    _sdrpp_environment,
    _stop_readsb_service,
    sync_sdrpp_theme,
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
        with patch.dict(
            os.environ,
            {"KEEP_ME": "yes", "LD_PRELOAD": "/tmp/libtermux-exec.so"},
            clear=True,
        ):
            environment = _sdrpp_environment(":1")

        self.assertEqual(":1", environment["DISPLAY"])
        self.assertEqual("yes", environment["KEEP_ME"])
        self.assertNotIn("LD_PRELOAD", environment)

    def test_termux_detection_uses_termux_version(self) -> None:
        with patch.dict(os.environ, {"TERMUX_VERSION": "0.118"}, clear=True):
            self.assertTrue(_is_termux())

    def test_termux_detection_uses_prefix(self) -> None:
        with patch.dict(os.environ, {"PREFIX": "/data/data/com.termux/files/usr"}, clear=True):
            self.assertTrue(_is_termux())

    def test_non_termux_environment_is_not_detected(self) -> None:
        with patch.dict(os.environ, {"PREFIX": "/usr"}, clear=True):
            self.assertFalse(_is_termux())

    @patch("apps.launchers.sdrpp_launcher._sdrpp_process_running", return_value=False)
    @patch("apps.launchers.sdrpp_launcher._is_termux", return_value=False)
    def test_native_theme_sync_preserves_config(
        self,
        _termux: Mock,
        _running: Mock,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "config.json"
            config.write_text(json.dumps({"theme": "Dark", "keep": 42}), encoding="utf-8")

            self.assertTrue(sync_sdrpp_theme("light", native_root=root))

            document = json.loads(config.read_text(encoding="utf-8"))
            self.assertEqual("Light", document["theme"])
            self.assertEqual(42, document["keep"])

    def test_launcher_rejects_unknown_theme(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported SDR\\+\\+ theme"):
            SDRPPLauncher(profile=self.profile, theme="neon apocalypse")

    @patch("apps.launchers.sdrpp_launcher.shutil.which")
    def test_native_launch_command_is_preserved(self, which: Mock) -> None:
        which.side_effect = lambda command: "/usr/bin/sdrpp" if command == "sdrpp" else None
        launcher = SDRPPLauncher(profile=self.profile)
        self.assertEqual(["/usr/bin/sdrpp", "--autostart"], launcher._launch_command(":0"))

    @patch("apps.launchers.sdrpp_launcher._is_termux", return_value=True)
    @patch("apps.launchers.sdrpp_launcher.shutil.which")
    def test_termux_launch_command_uses_debian_proot(self, which: Mock, _termux: Mock) -> None:
        which.side_effect = lambda command: (
            "/data/data/com.termux/files/usr/bin/proot-distro" if command == "proot-distro" else None
        )
        launcher = SDRPPLauncher(profile=self.profile)
        command = launcher._launch_command(":1")
        self.assertEqual("/data/data/com.termux/files/usr/bin/proot-distro", command[0])
        self.assertEqual(["login", "debian", "--shared-tmp", "--"], command[1:5])
        self.assertIn("DISPLAY=:1", command)
        self.assertIn("XDG_RUNTIME_DIR=/tmp/runtime-root", command)
        self.assertIn("XDG_SESSION_TYPE=x11", command)
        self.assertIn("GDK_BACKEND=x11", command)
        self.assertIn("LIBGL_ALWAYS_SOFTWARE=1", command)
        self.assertIn("mkdir -p /tmp/runtime-root", command[-1])
        self.assertIn("chmod 700 /tmp/runtime-root", command[-1])
        self.assertIn("cd /root/SDRPlusPlus", command[-1])
        self.assertIn("./build/sdrpp -r root_dev --autostart", command[-1])

    @patch("apps.launchers.sdrpp_launcher._sdrpp_process_running", return_value=False)
    @patch("apps.launchers.sdrpp_launcher._is_termux", return_value=True)
    @patch("apps.launchers.sdrpp_launcher.shutil.which", return_value="/usr/bin/proot-distro")
    @patch("apps.launchers.sdrpp_launcher.subprocess.run")
    def test_termux_theme_sync_runs_inside_proot(
        self,
        run: Mock,
        _which: Mock,
        _termux: Mock,
        _running: Mock,
    ) -> None:
        run.return_value.returncode = 0
        self.assertTrue(sync_sdrpp_theme("Dark"))
        command = run.call_args.args[0]
        self.assertEqual("/usr/bin/proot-distro", command[0])
        self.assertEqual(["login", "debian", "--shared-tmp", "--"], command[1:5])
        self.assertIn("/root/SDRPlusPlus/root_dev/config.json", command)
        self.assertEqual("Dark", command[-1])

    @patch("apps.launchers.sdrpp_launcher._is_termux", return_value=False)
    @patch("apps.launchers.sdrpp_launcher.shutil.which", return_value=None)
    def test_missing_native_executable_raises_outside_termux(self, _which: Mock, _termux: Mock) -> None:
        launcher = SDRPPLauncher(profile=self.profile)
        with self.assertRaisesRegex(RuntimeError, "Could not find sdrpp"):
            launcher._launch_command(":0")

    @patch("apps.launchers.sdrpp_launcher.shutil.which", return_value=None)
    @patch("apps.launchers.sdrpp_launcher._stop_readsb_service")
    def test_missing_executable_raises(self, _stop_readsb: Mock, _which: Mock) -> None:
        launcher = SDRPPLauncher(profile=self.profile)
        launcher.is_running = Mock(return_value=False)
        with patch("apps.launchers.sdrpp_launcher._is_termux", return_value=False):
            with self.assertRaisesRegex(RuntimeError, "Could not find sdrpp"):
                launcher.launch(":1")

    @patch("apps.launchers.sdrpp_launcher.subprocess.run")
    @patch("apps.launchers.sdrpp_launcher._is_termux", return_value=False)
    def test_readsb_stop_is_skipped_outside_termux(
        self,
        _termux: Mock,
        run: Mock,
    ) -> None:
        _stop_readsb_service()
        run.assert_not_called()

    @patch("apps.launchers.sdrpp_launcher.subprocess.run")
    @patch("apps.launchers.sdrpp_launcher.shutil.which", return_value=None)
    @patch("apps.launchers.sdrpp_launcher._is_termux", return_value=True)
    def test_readsb_stop_is_skipped_without_sv(
        self,
        _termux: Mock,
        _which: Mock,
        run: Mock,
    ) -> None:
        _stop_readsb_service()
        run.assert_not_called()

    @patch("apps.launchers.sdrpp_launcher.subprocess.run")
    @patch("apps.launchers.sdrpp_launcher.shutil.which")
    @patch("apps.launchers.sdrpp_launcher._is_termux", return_value=True)
    def test_readsb_stop_uses_termux_sv(
        self,
        _termux: Mock,
        which: Mock,
        run: Mock,
    ) -> None:
        which.side_effect = lambda command: (
            "/data/data/com.termux/files/usr/bin/sv" if command == "sv" else None
        )
        _stop_readsb_service()
        run.assert_called_once_with(
            ["/data/data/com.termux/files/usr/bin/sv", "down", "readsb"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )

    @patch("apps.launchers.sdrpp_launcher._stop_readsb_service")
    def test_existing_ready_process_does_not_spawn_another(self, stop_readsb: Mock) -> None:
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
    @patch("apps.launchers.sdrpp_launcher.subprocess.Popen")
    def test_existing_process_without_rigctl_is_restarted(
        self,
        popen: Mock,
        _stop_readsb: Mock,
    ) -> None:
        process = Mock()
        process.poll.return_value = None
        popen.return_value = process
        launcher = SDRPPLauncher(profile=self.profile)
        launcher.is_running = Mock(return_value=True)
        launcher.is_rigctl_ready = Mock(return_value=False)
        launcher.stop = Mock()
        launcher._launch_command = Mock(return_value=["/usr/bin/sdrpp", "--autostart"])
        launcher._request_fullscreen = Mock()
        launcher.wait_for_rigctl = Mock()

        launcher.launch(":1")

        launcher.stop.assert_called_once_with(":1", None)
        popen.assert_called_once()
        launcher.wait_for_rigctl.assert_called_once_with()

    @patch("apps.launchers.sdrpp_launcher._stop_readsb_service")
    @patch("apps.launchers.sdrpp_launcher.subprocess.Popen")
    def test_embedded_launch_does_not_request_fullscreen(self, popen: Mock, _stop_readsb: Mock) -> None:
        process = Mock()
        process.poll.return_value = None
        popen.return_value = process
        launcher = SDRPPLauncher(profile=self.profile, embedded=True, fullscreen=True)
        launcher.is_running = Mock(return_value=False)
        launcher._launch_command = Mock(return_value=["/usr/bin/sdrpp", "--autostart"])
        launcher.wait_for_rigctl = Mock()
        launcher._request_fullscreen = Mock()
        launcher.launch(":1")
        launcher._request_fullscreen.assert_not_called()
        launcher.wait_for_rigctl.assert_called_once_with()

    @patch("apps.launchers.sdrpp_launcher.close_matching_display_apps")
    @patch("apps.launchers.sdrpp_launcher.terminate_process")
    def test_stop_terminates_owned_process_and_closes_display_apps(self, terminate: Mock, close_apps: Mock) -> None:
        launcher = SDRPPLauncher(profile=self.profile)
        process = Mock()
        launcher._process = process
        status = Mock()
        launcher.stop(":1", status)
        terminate.assert_called_once_with(process)
        close_apps.assert_called_once_with(display=":1", patterns=("sdrpp", "sdr\\+\\+"))
        self.assertIsNone(launcher._process)
        status.assert_called_once_with("SDR++ stopped")

    @patch("apps.launchers.sdrpp_launcher._stop_readsb_service")
    def test_resource_manager_is_acquired_before_launch(self, _stop_readsb: Mock) -> None:
        resource_manager = Mock()
        launcher = SDRPPLauncher(profile=self.profile, resource_manager=resource_manager, owner_name="radio-fm")
        launcher.is_running = Mock(return_value=True)
        launcher.is_rigctl_ready = Mock(return_value=True)
        status = Mock()
        launcher.launch(":1", status)
        resource_manager.acquire.assert_called_once_with("radio-fm", force=True, set_status=status)


if __name__ == "__main__":
    unittest.main()
