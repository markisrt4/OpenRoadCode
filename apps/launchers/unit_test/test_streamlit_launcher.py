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


if __name__ == "__main__":
    unittest.main()
