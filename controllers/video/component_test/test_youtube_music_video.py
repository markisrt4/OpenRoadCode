# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import unittest

from controllers.video.youtube_music_video import YouTubeMusicVideo


class YouTubeMusicVideoTest(unittest.TestCase):
    def test_player_includes_return_to_carui_control(self) -> None:
        player = YouTubeMusicVideo()

        page = player._build_player_html(
            "video-id",
            position_ms=0,
        )

        self.assertIn("RETURN</button>", page)
        self.assertIn("return-to-carui", page)
        self.assertNotIn("RETURN TO CARUI", page)
        self.assertIn("/close", page)


if __name__ == "__main__":
    unittest.main()
