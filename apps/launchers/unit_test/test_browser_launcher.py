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


def test_owned_embedded_stop_uses_short_process_grace_without_window_or_proc_scan(tmp_path):
    launcher=BrowserKioskLauncher(url='http://127.0.0.1:1234',profile_path=tmp_path/'profile',log_file=tmp_path/'browser.log')
    process=Mock()
    process.poll.return_value=None
    launcher._process=process
    with (patch('apps.launchers.browser_launcher.terminate_process') as terminate,
          patch('apps.launchers.browser_launcher.close_matching_display_apps') as scan,
          patch.object(launcher,'_close_app_window') as window):
        launcher.stop(':1',owned_process_only=True)
    terminate.assert_called_once_with(process,timeout_seconds=1.0)
    scan.assert_not_called()
    window.assert_not_called()
    assert launcher._process is None


def test_profile_stop_waits_for_surviving_browser_after_wrapper_exit(tmp_path):
    launcher = BrowserKioskLauncher(url='https://example.com',
        profile_path=tmp_path / 'profile', process_pattern='owned-profile')
    process = Mock()
    process.poll.return_value = 3
    launcher._process = process
    with patch('apps.launchers.browser_launcher.close_matching_display_apps') as close, patch(
        'apps.launchers.browser_launcher.is_process_running', side_effect=[True, True, False]) as running, patch(
        'apps.launchers.browser_launcher.time.sleep') as wait, patch.object(
        launcher, '_close_app_window', return_value=False), patch(
        'apps.launchers.browser_launcher.terminate_process'):
        launcher.stop(':1')
    close.assert_called_once_with(display=':1', patterns=('owned-profile',))
    assert running.call_count == 3
    assert wait.call_count == 2


def test_profile_still_running_blocks_reopen_instead_of_claiming_cleanup(tmp_path):
    import pytest
    launcher = BrowserKioskLauncher(url='https://example.com',
        profile_path=tmp_path / 'profile', process_pattern='owned-profile')
    with patch('apps.launchers.browser_launcher.close_matching_display_apps'), patch(
        'apps.launchers.browser_launcher.is_process_running', return_value=True), patch(
        'apps.launchers.browser_launcher.time.monotonic', side_effect=[0, 2]):
        with pytest.raises(RuntimeError, match='profile is still running'):
            launcher.stop(':1')


def test_startup_exit_three_remains_an_error_instead_of_adopting_a_window(tmp_path):
    import pytest
    launcher = BrowserKioskLauncher(url='https://example.com',
        log_file=tmp_path / 'browser.log', startup_grace_seconds=0.2)
    process = Mock()
    process.poll.return_value = 3
    with patch.object(launcher, 'is_running', return_value=False), patch.object(
        launcher, '_find_browser', return_value='/usr/bin/chromium'), patch(
        'apps.launchers.browser_launcher.subprocess.Popen', return_value=process), patch(
        'apps.launchers.browser_launcher.time.sleep'), patch.object(launcher, '_fit_app_window') as fit:
        with pytest.raises(RuntimeError, match='startup \\(status 3\\)'):
            launcher.launch(':1')
    fit.assert_not_called()
    assert launcher._process is None
