"""Tests for YouTube destination startup behavior."""

import unittest
from unittest.mock import Mock, patch

from apps.carUi.screens.youtube_screen import YouTubeScreen


class YouTubeScreenTest(unittest.TestCase):
    @patch("apps.carUi.screens.youtube_screen.YouTubePanel")
    def test_show_opens_youtube_home_after_layout(self, panel_type: Mock) -> None:
        host = Mock()
        panel = panel_type.return_value
        screen = YouTubeScreen(
            host,
            player=Mock(),
            display=":0",
            colors={},
            back_action=Mock(),
        )

        screen.show()

        panel.pack.assert_called_once_with(fill="both", expand=True)
        panel.update_idletasks.assert_called_once_with()
        panel.open_home.assert_called_once_with()
        host.set_screen_status.assert_called_once_with("Opening YouTube home")


if __name__ == "__main__":
    unittest.main()
