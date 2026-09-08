# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for deferred Spotify screen hydration."""

import unittest
from unittest.mock import Mock, patch

from frontends.tk.media.spotify_screen import SpotifyScreen


class SpotifyScreenTest(unittest.TestCase):
    @patch("frontends.tk.media.spotify_screen.threading.Thread")
    @patch("frontends.tk.media.spotify_screen.SpotifyVideoOverlay")
    @patch("frontends.tk.media.spotify_screen.tk.Frame")
    @patch("frontends.tk.media.spotify_screen._ThreadSafeSpotifyPlaybackPanel")
    def test_show_paints_panel_before_loading_state(
        self,
        panel_type: Mock,
        frame_type: Mock,
        _video_overlay_type: Mock,
        thread_type: Mock,
    ) -> None:
        host = Mock()
        scheduled: list[tuple[int, object]] = []

        def schedule(delay_ms: int, callback: object) -> str:
            scheduled.append((delay_ms, callback))
            return f"job-{len(scheduled)}"

        host.schedule_ui_callback.side_effect = schedule
        frame_type.return_value = Mock()
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

        hydration_callbacks = [
            callback for delay_ms, callback in scheduled if delay_ms == 1
        ]
        self.assertEqual(1, len(hydration_callbacks))

        hydration_callbacks[0]()  # type: ignore[operator]

        thread_type.assert_called_once()
        thread_type.return_value.start.assert_called_once_with()
        panel.set_media_state.assert_not_called()


if __name__ == "__main__":
    unittest.main()
