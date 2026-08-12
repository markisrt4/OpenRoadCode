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

    def test_deferred_volume_error_retains_exception(self) -> None:
        expected_error = RuntimeError("volume unavailable")
        handler = Mock()
        handler.request_volume.side_effect = expected_error
        callbacks = []
        panel = SimpleNamespace(
            _destroyed=False,
            _pending_volume_percent=45,
            _volume_request=3,
            _volume_worker_active=True,
            _volume_handler=handler,
            _finish_volume_adjustment=Mock(),
            after=lambda _delay, callback: callbacks.append(callback),
        )

        SpotifyPlaybackPanel._set_volume_worker(panel)  # type: ignore[arg-type]
        callbacks[0]()

        panel._finish_volume_adjustment.assert_called_once_with(
            request=3,
            error=expected_error,
        )


if __name__ == "__main__":
    unittest.main()
