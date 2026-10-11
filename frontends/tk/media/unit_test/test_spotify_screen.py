# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for composition session binding and live theme refresh."""

import unittest
from unittest.mock import Mock, patch

from frontends.tk.media.spotify_screen import SpotifyScreen


def _theme() -> dict:
    """Return the minimum valid Spotify theme consumed by the screen."""
    return {
        "colors": {"background": "#121212"},
        "layout": {"refresh_interval_ms": 1000},
    }


class SpotifyScreenTest(unittest.TestCase):
    @patch("frontends.tk.media.spotify_screen.SpotifyVideoOverlay")
    @patch("frontends.tk.media.spotify_screen.tk.Frame")
    @patch("frontends.tk.media.spotify_screen.SpotifyPlaybackPanel")
    def test_show_binds_painted_view_and_hide_retires_session(self, panel_type, frame_type, overlay_type):
        host, session = Mock(), Mock()
        screen = SpotifyScreen(
            host, theme=_theme(), back_action=Mock(),
            playback_session=session, native_surface=Mock(),
        )
        screen.show()
        panel = panel_type.return_value
        panel.pack.assert_called_once_with(fill="both", expand=True)
        session.activate.assert_called_once_with(screen)
        session.deactivate.reset_mock()
        screen.hide()
        session.deactivate.assert_called_once_with()
        overlay_type.return_value.close.assert_called_once_with()

    def test_theme_change_rebuilds_visible_now_playing_view(self) -> None:
        screen = SpotifyScreen(
            Mock(), theme=_theme(), back_action=Mock(),
            playback_session=Mock(), native_surface=Mock(),
        )
        screen._visible = True
        screen._view = "now"

        with patch.object(screen, "_show_now_playing") as show_now_playing:
            screen.set_theme_mode(object())

        show_now_playing.assert_called_once_with()

    def test_theme_change_does_not_rebuild_hidden_screen(self) -> None:
        screen = SpotifyScreen(
            Mock(), theme=_theme(), back_action=Mock(),
            playback_session=Mock(), native_surface=Mock(),
        )

        with patch.object(screen, "_show_now_playing") as show_now_playing:
            screen.set_theme_mode(object())

        show_now_playing.assert_not_called()


if __name__ == "__main__":
    unittest.main()
