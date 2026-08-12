# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for Netflix destination startup behavior."""

import unittest
from unittest.mock import Mock, patch

from apps.carUi.screens.netflix_screen import NetflixScreen


class NetflixScreenTest(unittest.TestCase):
    @patch("apps.carUi.screens.netflix_screen.NetflixPanel")
    def test_show_opens_netflix_after_layout(self, panel_type: Mock) -> None:
        host = Mock()
        panel = panel_type.return_value
        screen = NetflixScreen(
            host,
            player=Mock(),
            display=":2",
            colors={},
            back_action=Mock(),
        )

        screen.show()

        panel.pack.assert_called_once_with(fill="both", expand=True)
        panel.update_idletasks.assert_called_once_with()
        panel.open_home.assert_called_once_with()
        host.set_screen_status.assert_called_once_with("Opening Netflix")


if __name__ == "__main__":
    unittest.main()
