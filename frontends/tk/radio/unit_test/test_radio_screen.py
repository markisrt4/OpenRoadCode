# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for live radio theme propagation."""

import unittest
from unittest.mock import Mock

from frontends.tk.radio.radio_screen import RadioScreen
from ui.theme import ThemeMode


class RadioScreenTest(unittest.TestCase):
    def test_theme_change_updates_visible_panel_and_external_sdr(self) -> None:
        host = Mock()
        bundle = Mock()
        sync_theme = Mock()
        screen = RadioScreen(
            host,
            theme_bundle=lambda: bundle,
            theme_mode=lambda: ThemeMode.DARK,
            panel_factory=Mock(),
            embedder=Mock(),
            sync_theme=sync_theme,
        )
        panel = Mock()
        panel.winfo_exists.return_value = True
        screen._panel = panel

        screen.set_theme_mode(ThemeMode.LIGHT)

        panel.set_theme_bundle.assert_called_once_with(bundle)
        sync_theme.assert_called_once_with(ThemeMode.LIGHT)

    def test_theme_change_still_updates_external_sdr_when_screen_hidden(self) -> None:
        sync_theme = Mock()
        screen = RadioScreen(
            Mock(),
            theme_bundle=Mock(),
            theme_mode=lambda: ThemeMode.DARK,
            panel_factory=Mock(),
            embedder=Mock(),
            sync_theme=sync_theme,
        )

        screen.set_theme_mode(ThemeMode.LIGHT)

        sync_theme.assert_called_once_with(ThemeMode.LIGHT)


if __name__ == "__main__":
    unittest.main()


def test_hiding_radio_retires_streaming_panel_before_detaching_native_window():
    embedder, panel = Mock(), Mock()
    events = []
    panel.deactivate.side_effect = lambda: events.append("deactivate")
    panel.detach_sdrpp.side_effect = lambda parent: events.append("detach")
    embedder.clear.side_effect = lambda: events.append("clear")
    screen = RadioScreen(
        Mock(), theme_bundle=Mock(), theme_mode=lambda: ThemeMode.DARK,
        panel_factory=Mock(), embedder=embedder,
    )
    screen._panel = panel
    screen.hide()
    assert events == ["deactivate", "detach", "clear"]
