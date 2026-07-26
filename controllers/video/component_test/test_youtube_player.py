from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from controllers.video.youtube_player import YouTubePlayer


class YouTubePlayerTest(unittest.TestCase):
    def test_resolves_search_and_youtube_urls(self) -> None:
        self.assertEqual(
            "https://www.youtube.com/results?search_query=road+trip+music",
            YouTubePlayer.resolve_target("road trip music"),
        )
        self.assertEqual(
            "https://youtu.be/abc123",
            YouTubePlayer.resolve_target(" https://youtu.be/abc123 "),
        )

    def test_rejects_non_youtube_url(self) -> None:
        with self.assertRaises(ValueError):
            YouTubePlayer.resolve_target("https://example.com/video")

    @patch("controllers.video.youtube_player.BrowserKioskLauncher")
    def test_launches_browser_app_aligned_to_panel(
        self,
        launcher_type: MagicMock,
    ) -> None:
        launcher = launcher_type.return_value
        player = YouTubePlayer(profile_path="/tmp/youtube-test-profile")

        self.assertTrue(
            player.play(
                "music videos",
                display=":2",
                window_position=(18, 72),
                window_size=(1244, 590),
            )
        )

        options = launcher_type.call_args.kwargs
        self.assertTrue(options["app_mode"])
        self.assertFalse(options["kiosk"])
        self.assertEqual((18, 72), options["window_position"])
        self.assertEqual((1244, 590), options["window_size"])
        launcher.launch.assert_called_once_with(":2")

        player.stop()
        launcher.stop.assert_called_once_with(":2")


if __name__ == "__main__":
    unittest.main()
