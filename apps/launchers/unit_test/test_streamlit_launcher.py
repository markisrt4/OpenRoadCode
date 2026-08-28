# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for Streamlit server warm-up behavior."""

import unittest
from unittest.mock import Mock, patch

from apps.launchers.streamlit_launcher import StreamlitLauncher


class StreamlitLauncherTest(unittest.TestCase):
    @patch("apps.launchers.streamlit_launcher.Path.is_file", return_value=True)
    def test_prepare_starts_server_without_browser(self, _is_file: Mock) -> None:
        launcher = StreamlitLauncher(app_path="dashboard.py")
        launcher.is_running = Mock(return_value=False)
        launcher._start_server = Mock()
        launcher._wait_for_server = Mock(return_value=True)

        launcher.prepare()

        launcher._start_server.assert_called_once_with()
        launcher._wait_for_server.assert_called_once_with()
        self.assertIsNone(launcher.browser._process)

    @patch("apps.launchers.streamlit_launcher.Path.is_file", return_value=True)
    def test_prepare_raises_when_server_never_becomes_reachable(
        self, _is_file: Mock
    ) -> None:
        launcher = StreamlitLauncher(app_path="dashboard.py", port=8765)
        launcher.is_running = Mock(return_value=False)
        launcher._start_server = Mock()
        launcher._wait_for_server = Mock(return_value=False)

        with self.assertRaisesRegex(
            RuntimeError,
            "Streamlit server did not become reachable at http://127.0.0.1:8765",
        ):
            launcher.prepare()

    @patch("apps.launchers.streamlit_launcher.Path.is_file", return_value=True)
    def test_launch_does_not_open_browser_when_server_startup_fails(
        self, _is_file: Mock
    ) -> None:
        browser = Mock()
        launcher = StreamlitLauncher(app_path="dashboard.py", browser=browser)
        launcher.prepare = Mock(side_effect=RuntimeError("server failed"))

        with self.assertRaisesRegex(RuntimeError, "server failed"):
            launcher.launch(":1")

        browser.launch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
