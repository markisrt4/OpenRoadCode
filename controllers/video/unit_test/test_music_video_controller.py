# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for track-specific music-video availability."""

import unittest
import threading
from unittest.mock import Mock
from dataclasses import replace

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

    def test_offline_never_queries_spotify_or_video_provider(self) -> None:
        controller = MusicVideoController(self.spotify, self.video, network_allowed=lambda: False)
        self.assertFalse(controller.current_track_has_video())
        self.assertFalse(controller.watch_current_track())
        self.spotify.current_state.assert_not_called()
        self.video.find_video.assert_not_called()
        self.video.play_video.assert_not_called()
        controller.stop_video()
        self.video.stop_video.assert_called_once_with()

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

    def test_cancelled_video_lookup_does_not_pause_or_launch(self) -> None:
        current = [True]
        def find(_query):
            current[0] = False
            return MusicVideo("id", "Road Song", "Open Band")
        self.video.find_video.side_effect = find
        self.assertFalse(self.controller.watch_current_track(is_current=lambda: current[0]))
        self.spotify.pause.assert_not_called()
        self.video.play_video.assert_not_called()

    def test_cancelled_launch_stops_video_and_restores_spotify(self) -> None:
        current = [True]
        self.spotify.current_state.return_value = replace(self.spotify.current_state.return_value, is_playing=True)
        self.video.find_video.return_value = MusicVideo("id", "Road Song", "Open Band")
        def launch(*_args, **_kwargs):
            current[0] = False
            return True
        self.video.play_video.side_effect = launch
        self.assertFalse(self.controller.watch_current_track(is_current=lambda: current[0]))
        self.video.stop_video.assert_called_once_with()
        self.spotify.play.assert_called_once_with()

    def test_terminal_cancellation_stops_video_without_restarting_audio(self) -> None:
        current = [True]
        self.spotify.current_state.return_value = replace(self.spotify.current_state.return_value, is_playing=True)
        self.video.find_video.return_value = MusicVideo("id", "Road Song", "Open Band")
        def launch(*_args, **_kwargs):
            current[0] = False
            return True
        self.video.play_video.side_effect = launch
        self.assertFalse(self.controller.watch_current_track(
            is_current=lambda: current[0], restore_allowed=lambda: False))
        self.video.stop_video.assert_called_once_with()
        self.spotify.play.assert_not_called()

    def test_retired_return_does_not_touch_backend(self) -> None:
        self.controller.return_to_spotify(is_current=lambda: False)
        self.spotify.seek_to_position_ms.assert_not_called()
        self.spotify.play.assert_not_called()
        self.spotify.pause.assert_not_called()
        self.video.stop_video.assert_not_called()

    def test_new_launch_waits_for_retired_launch_cleanup(self) -> None:
        entered, release, second_entered = threading.Event(), threading.Event(), threading.Event()
        current = [True]
        events = []
        results = []
        self.spotify.current_state.return_value = replace(self.spotify.current_state.return_value, is_playing=True)
        self.video.find_video.return_value = MusicVideo("id", "Road Song", "Open Band")
        def launch(*_args, **_kwargs):
            if not entered.is_set():
                events.append("start-old")
                entered.set()
                release.wait(2)
            else:
                events.append("start-new")
            return True
        self.video.play_video.side_effect = launch
        self.video.stop_video.side_effect = lambda: events.append("stop-old")
        self.spotify.play.side_effect = lambda: events.append("restore")
        first = threading.Thread(target=lambda: results.append(self.controller.watch_current_track(is_current=lambda: current[0])))
        def start_second():
            second_entered.set()
            results.append(self.controller.watch_current_track())
        second = threading.Thread(target=start_second)
        try:
            first.start()
            self.assertTrue(entered.wait(1))
            current[0] = False
            second.start()
            self.assertTrue(second_entered.wait(1))
        finally:
            release.set()
            first.join(timeout=2)
            if second.ident is not None:
                second.join(timeout=2)
        self.assertFalse(first.is_alive())
        self.assertFalse(second.is_alive())
        self.assertEqual(events, ["start-old", "stop-old", "restore", "start-new"])
        self.assertEqual(results, [False, True])


if __name__ == "__main__":
    unittest.main()
