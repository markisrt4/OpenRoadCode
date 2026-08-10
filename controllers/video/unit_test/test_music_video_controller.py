"""Tests for track-specific music-video availability."""

import unittest
from unittest.mock import Mock

from controllers.spotify.spotify_state import SpotifyState
from controllers.video.music_video_controller import MusicVideoController
from controllers.video.music_video_types import MusicVideo


class MusicVideoControllerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.spotify = Mock()
        self.video = Mock()
        self.controller = MusicVideoController(self.spotify, self.video)
        self.spotify.current_state.return_value = SpotifyState(
            is_available=True,
            track_name="Road Song",
            artist_name="Open Band",
            album_name="Long Drive",
            progress_ms=12_000,
            duration_ms=180_000,
        )

    def test_unmatched_track_is_reported_unavailable(self) -> None:
        self.video.find_video.return_value = None

        self.assertFalse(self.controller.current_track_has_video())
        self.assertFalse(self.controller.current_track_has_video())

        self.video.find_video.assert_called_once()

    def test_prepared_video_is_reused_when_playback_is_requested(self) -> None:
        match = MusicVideo("id", "Road Song", "Open Band")
        self.video.find_video.return_value = match
        self.video.play_video.return_value = True

        self.assertTrue(self.controller.current_track_has_video())
        self.assertTrue(self.controller.watch_current_track())

        self.video.find_video.assert_called_once()
        self.video.play_video.assert_called_once_with(
            match,
            position_ms=12_000,
        )


if __name__ == "__main__":
    unittest.main()
