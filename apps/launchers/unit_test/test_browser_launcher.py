"""Tests for browser process lifecycle behavior."""

import unittest
from unittest.mock import Mock, patch

from apps.launchers.browser_launcher import BrowserKioskLauncher


class BrowserKioskLauncherTest(unittest.TestCase):
    def tearDown(self) -> None:
        BrowserKioskLauncher._exclusive_launchers.clear()

    def test_exclusive_launcher_closes_peer_on_same_display(self) -> None:
        peer = Mock()
        BrowserKioskLauncher._exclusive_launchers[("dashboards", ":0")] = peer
        launcher = BrowserKioskLauncher(
            url="https://example.com",
            exclusive_group="dashboards",
        )

        launcher._close_exclusive_peer(":0")

        peer.stop.assert_called_once_with(":0")

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
