# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Non-visual regression tests for Spotify panel callbacks."""

import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from frontends.tk.media.spotify_playback_panel import SpotifyPlaybackPanel


class SpotifyPlaybackPanelTest(unittest.TestCase):
    def test_long_title_shrinks_within_fixed_width(self) -> None:
        label = Mock()
        label.winfo_width.return_value = 300
        panel = SimpleNamespace(
            _track_label=label,
            _track_var=SimpleNamespace(get=lambda: "x" * 20),
            _style={
                "track_font": ("Sans", 28, "bold"),
                "minimum_track_font_size": 12,
                "minimum_title_wrap": 180,
            },
        )

        with patch(
            "frontends.tk.media.spotify_playback_panel.tkfont.Font",
            side_effect=lambda **options: SimpleNamespace(
                measure=lambda title: len(title) * options["size"]
            ),
        ):
            SpotifyPlaybackPanel._fit_track_title(  # type: ignore[arg-type]
                panel, 300
            )

        label.configure.assert_called_once_with(
            font=("Sans", 15, "bold"),
            wraplength=0,
        )

    def test_volume_click_emits_request_without_running_worker(self) -> None:
        handler = Mock()
        panel = SimpleNamespace(
            _displayed_volume_percent=40, _volume_handler=handler,
            _layout={"default_volume": 50, "minimum_volume": 0, "maximum_volume": 100},
        )
        SpotifyPlaybackPanel._adjust_volume(panel, 5)
        handler.request_volume.assert_called_once_with(45)



if __name__ == "__main__":
    unittest.main()
