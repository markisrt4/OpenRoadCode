# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for browser process lifecycle behavior."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

from apps.launchers.browser_launcher import BrowserKioskLauncher


class BrowserKioskLauncherTest(unittest.TestCase):
    def test_launch_restores_existing_browser_window(self) -> None:
        launcher = BrowserKioskLauncher(url="https://example.com", window_class="example")
        launcher._hidden = True

        with (
            patch.object(launcher, "is_running", return_value=True),
            patch.object(launcher, "_activate_existing_window") as activate,
        ):
            launcher.launch(":0")

        activate.assert_called_once_with(":0")
        self.assertFalse(launcher._hidden)

    def test_launch_uses_basic_password_store(self) -> None:
        with TemporaryDirectory() as temporary:
            launcher = BrowserKioskLauncher(
                url="https://example.com",
                log_file=Path(temporary) / "browser.log",
            )
            process = Mock()
            process.poll.return_value = None

            with (
                patch.object(launcher, "is_running", return_value=False),
                patch.object(launcher, "_find_browser", return_value="/usr/bin/chromium"),
                patch("apps.launchers.browser_launcher.x11_environment", return_value={"DISPLAY": ":1"}),
                patch("apps.launchers.browser_launcher.subprocess.Popen", return_value=process) as popen,
            ):
                launcher.launch(":1")

            command = popen.call_args.args[0]
            self.assertIn("--password-store=basic", command)

    @patch("apps.launchers.browser_launcher.close_matching_display_apps")
    @patch("apps.launchers.browser_launcher.terminate_process")
    def test_stop_allows_normal_window_close_to_save_profile(
        self,
        terminate_process: Mock,
        close_matching_display_apps: Mock,
    ) -> None:
        launcher = BrowserKioskLauncher(url="https://example.com")
        process = Mock()
        process.poll.return_value = 0
        launcher._process = process
        launcher._window_id = "0x123"

        with (
            patch.object(launcher, "_close_app_window", return_value=True),
            patch.object(launcher, "_wait_for_process_exit") as wait_for_exit,
        ):
            launcher.stop(":2")

        wait_for_exit.assert_called_once_with(process)
        terminate_process.assert_not_called()
        close_matching_display_apps.assert_not_called()

    @patch("apps.launchers.browser_launcher.close_matching_display_apps")
    @patch("apps.launchers.browser_launcher.terminate_process")
    def test_stop_forces_shutdown_when_normal_close_is_unavailable(
        self,
        terminate_process: Mock,
        close_matching_display_apps: Mock,
    ) -> None:
        launcher = BrowserKioskLauncher(url="https://example.com")
        process = Mock()
        process.poll.return_value = None
        launcher._process = process

        with (
            patch.object(launcher, "_close_app_window", return_value=False),
            patch.object(launcher, "_wait_for_process_exit") as wait_for_exit,
        ):
            launcher.stop(":0")

        wait_for_exit.assert_not_called()
        terminate_process.assert_called_once_with(process)
        close_matching_display_apps.assert_called_once()


if __name__ == "__main__":
    unittest.main()
