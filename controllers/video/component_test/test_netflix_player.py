# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from controllers.video.netflix_player import NetflixPlayer


class NetflixPlayerComponentTest(unittest.TestCase):
    def test_accepts_netflix_https_urls(self) -> None:
        self.assertEqual(
            "https://www.netflix.com/watch/12345",
            NetflixPlayer.validate_url(
                " https://www.netflix.com/watch/12345 "
            ),
        )

    def test_rejects_non_netflix_and_non_https_urls(self) -> None:
        invalid_urls = (
            "http://www.netflix.com/watch/12345",
            "https://netflix.com.example.org/watch/12345",
            "https://example.org/watch/12345",
        )
        for url in invalid_urls:
            with self.subTest(url=url), self.assertRaises(ValueError):
                NetflixPlayer.validate_url(url)

    @patch("controllers.video.netflix_player.BrowserKioskLauncher")
    def test_launches_browser_app_aligned_to_panel(
        self,
        launcher_type: MagicMock,
    ) -> None:
        launcher = launcher_type.return_value
        player = NetflixPlayer(profile_path="/tmp/netflix-test-profile")

        started = player.play(
            "https://www.netflix.com/watch/12345",
            display=":2",
            window_position=(18, 72),
            window_size=(1244, 590),
        )

        self.assertTrue(started)
        launcher_type.assert_called_once()
        options = launcher_type.call_args.kwargs
        self.assertTrue(options["app_mode"])
        self.assertFalse(options["kiosk"])
        self.assertEqual((18, 72), options["window_position"])
        self.assertEqual((1244, 590), options["window_size"])
        launcher.launch.assert_called_once_with(":2")

        player.stop()
        launcher.stop.assert_called_once_with(":2")

    @patch("controllers.video.netflix_player.BrowserKioskLauncher")
    def test_linux_dev_disables_gpu_acceleration(
        self, launcher_type: MagicMock
    ) -> None:
        player = NetflixPlayer(software_rendering=True)
        player.play("https://www.netflix.com/browse", display=":0")

        arguments = launcher_type.call_args.kwargs["extra_arguments"]
        self.assertIn("--disable-gpu", arguments)
        self.assertIn("--disable-gpu-compositing", arguments)
        self.assertIn(
            "--disable-features=VaapiVideoDecoder,VaapiVideoEncoder",
            arguments,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
