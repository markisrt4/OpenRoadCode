# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import unittest

from controllers.audio.streaming_audio_player_if import StreamingAudioPlayerIf
from controllers.radio.streaming_radio_controller import StreamingRadioController
from controllers.radio.streaming_radio_types import StreamingRadioStation


class _FakeStreamingAudioPlayer(StreamingAudioPlayerIf):
    def __init__(self) -> None:
        self.played_urls: list[str] = []
        self.stop_count = 0
        self._is_playing = False
        self.play_error: Exception | None = None

    @property
    def is_playing(self) -> bool:
        return self._is_playing

    def play(self, stream_url: str) -> None:
        if self.play_error is not None:
            raise self.play_error
        self.played_urls.append(stream_url)
        self._is_playing = True

    def stop(self) -> None:
        self.stop_count += 1
        self._is_playing = False


class StreamingRadioControllerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.player = _FakeStreamingAudioPlayer()
        self.controller = StreamingRadioController(self.player)
        self.station = StreamingRadioStation(
            station_id="station-1",
            name="Test FM",
            stream_url="https://example.test/live.mp3",
        )

    def test_play_delegates_stream_url_and_sets_current_station(self) -> None:
        self.controller.play(self.station)

        self.assertEqual(self.player.played_urls, [self.station.stream_url])
        self.assertIs(self.controller.current_station, self.station)
        self.assertTrue(self.controller.is_playing)

    def test_stop_delegates_and_clears_current_station(self) -> None:
        self.controller.play(self.station)

        self.controller.stop()

        self.assertEqual(self.player.stop_count, 1)
        self.assertIsNone(self.controller.current_station)
        self.assertFalse(self.controller.is_playing)

    def test_failed_play_does_not_replace_current_station(self) -> None:
        self.controller.play(self.station)
        replacement = StreamingRadioStation(
            station_id="station-2",
            name="Broken FM",
            stream_url="https://example.test/broken.mp3",
        )
        self.player.play_error = RuntimeError("player failed")

        with self.assertRaisesRegex(RuntimeError, "player failed"):
            self.controller.play(replacement)

        self.assertIs(self.controller.current_station, self.station)


if __name__ == "__main__":
    unittest.main()
