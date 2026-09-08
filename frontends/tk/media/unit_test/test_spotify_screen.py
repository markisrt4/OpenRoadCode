# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for deferred Spotify screen hydration and live theme refresh."""

import unittest
from unittest.mock import Mock, patch

from frontends.tk.media.spotify_screen import SpotifyScreen


class SpotifyScreenTest(unittest.TestCase):
    @patch("frontends.tk.media.spotify_screen.threading.Thread")
    @patch("frontends.tk.media.spotify_screen._ThreadSafeSpotifyPlaybackPanel")
    def test_show_paints_panel_before_loading_state(
        self,
        panel_type: Mock,
        thread_type: Mock,
    ) -> None:
        host = Mock()
        scheduled: list[object] = []

        def schedule(_delay_ms: int, callback: object) -> str:
            scheduled.append(callback)
            return "hydrate-job"

        host.schedule_ui_callback.side_effect = schedule
        panel = panel_type.return_value
        state_loader = Mock()
        screen = SpotifyScreen(
            host,
            theme={"layout": {"refresh_interval_ms": 1000}},
            back_action=Mock(),
            image_cache=Mock(),
            lyrics_client=Mock(),
            music_video_controller=Mock(),
            music_video_presentation=Mock(),
        )
        screen.set_state_loader(state_loader)

        screen.show()

        panel.pack.assert_called_once_with(fill="both", expand=True)
        panel.set_media_state.assert_not_called()
        state_loader.assert_not_called()
        self.assertEqual(len(scheduled), 1)

        scheduled[0]()  # type: ignore[operator]

        thread_type.assert_called_once()
        thread_type.return_value.start.assert_called_once_with()
        panel.set_media_state.assert_not_called()

    def test_theme_change_rebuilds_visible_now_playing_view(self) -> None:
        screen = SpotifyScreen(
            Mock(),
            theme={"layout": {"refresh_interval_ms": 1000}},
            back_action=Mock(),
            image_cache=Mock(),
            lyrics_client=Mock(),
            music_video_controller=Mock(),
            music_video_presentation=Mock(),
        )
        screen._visible = True
        screen._view = "now"

        with patch.object(screen, "_show_now_playing") as show_now_playing:
            screen.set_theme_mode(object())

        show_now_playing.assert_called_once_with()

    def test_theme_change_does_not_rebuild_hidden_screen(self) -> None:
        screen = SpotifyScreen(
            Mock(),
            theme={"layout": {"refresh_interval_ms": 1000}},
            back_action=Mock(),
            image_cache=Mock(),
            lyrics_client=Mock(),
            music_video_controller=Mock(),
            music_video_presentation=Mock(),
        )

        with patch.object(screen, "_show_now_playing") as show_now_playing:
            screen.set_theme_mode(object())

        show_now_playing.assert_not_called()


if __name__ == "__main__":
    unittest.main()
