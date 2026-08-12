# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for deferred Spotify screen hydration."""

import unittest
from unittest.mock import Mock, patch

from frontends.tk.media.spotify_screen import SpotifyScreen


class SpotifyScreenTest(unittest.TestCase):
    @patch("frontends.tk.media.spotify_screen.threading.Thread")
    @patch("frontends.tk.media.spotify_screen.SpotifyPlaybackPanel")
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


if __name__ == "__main__":
    unittest.main()
