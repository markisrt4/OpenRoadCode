# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for live radio theme propagation."""

import unittest
from unittest.mock import Mock, patch

from frontends.tk.radio.radio_screen import RadioScreen
from ui.theme import ThemeMode


class RadioScreenTest(unittest.TestCase):
    @patch("frontends.tk.radio.radio_screen.X11WindowEmbedder")
    def test_theme_change_updates_visible_panel_and_external_sdr(self, _embedder: Mock) -> None:
        host = Mock()
        bundle = Mock()
        sync_theme = Mock()
        screen = RadioScreen(
            host,
            theme_bundle=lambda: bundle,
            theme_mode=lambda: ThemeMode.DARK,
            panel_factory=Mock(),
            sync_theme=sync_theme,
        )
        panel = Mock()
        panel.winfo_exists.return_value = True
        screen._panel = panel

        screen.set_theme_mode(ThemeMode.LIGHT)

        panel.set_theme_bundle.assert_called_once_with(bundle)
        sync_theme.assert_called_once_with(ThemeMode.LIGHT)

    @patch("frontends.tk.radio.radio_screen.X11WindowEmbedder")
    def test_theme_change_still_updates_external_sdr_when_screen_hidden(self, _embedder: Mock) -> None:
        sync_theme = Mock()
        screen = RadioScreen(
            Mock(),
            theme_bundle=Mock(),
            theme_mode=lambda: ThemeMode.DARK,
            panel_factory=Mock(),
            sync_theme=sync_theme,
        )

        screen.set_theme_mode(ThemeMode.LIGHT)

        sync_theme.assert_called_once_with(ThemeMode.LIGHT)


if __name__ == "__main__":
    unittest.main()
