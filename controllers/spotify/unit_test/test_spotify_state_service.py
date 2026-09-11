# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for the controller-owned Spotify state service."""

import unittest
from unittest.mock import Mock

from controllers.spotify.spotify_state_service import SpotifyStateService


class SpotifyStateServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.backend = Mock()
        self.service = SpotifyStateService(self.backend)

    def test_play_request_is_queued_until_worker_drain(self) -> None:
        self.service.request_play()

        self.backend.play.assert_not_called()
        self.assertTrue(self.service._drain_commands())
        self.backend.play.assert_called_once_with()

    def test_volume_request_is_clamped_before_backend_call(self) -> None:
        self.service.request_volume(140)

        self.service._drain_commands()

        self.backend.set_volume_percent.assert_called_once_with(100)

    def test_library_results_are_cached(self) -> None:
        tracks = (Mock(), Mock())
        self.backend.saved_tracks.return_value = tracks

        first = self.service.load_saved_tracks(limit=20)
        second = self.service.load_saved_tracks(limit=20)

        self.assertEqual(tracks, first)
        self.assertEqual(tracks, second)
        self.backend.saved_tracks.assert_called_once_with(limit=20)

    def test_refresh_interval_rejects_too_fast_polling(self) -> None:
        with self.assertRaisesRegex(ValueError, "at least 5.0 seconds"):
            SpotifyStateService(self.backend, refresh_seconds=1.0)


if __name__ == "__main__":
    unittest.main()
