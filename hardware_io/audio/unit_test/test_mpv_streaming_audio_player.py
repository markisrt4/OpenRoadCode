# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import subprocess
import unittest
from unittest.mock import Mock, patch

from hardware_io.audio.mpv_streaming_audio_player import MpvStreamingAudioPlayer


class MpvStreamingAudioPlayerTest(unittest.TestCase):
    @patch("hardware_io.audio.mpv_streaming_audio_player.subprocess.Popen")
    @patch("hardware_io.audio.mpv_streaming_audio_player.shutil.which")
    def test_play_launches_audio_only_mpv(self, which: Mock, popen: Mock) -> None:
        which.return_value = "/usr/bin/mpv"
        process = Mock()
        process.poll.return_value = None
        popen.return_value = process
        player = MpvStreamingAudioPlayer()

        player.play("https://example.test/live.mp3")

        popen.assert_called_once_with(
            [
                "/usr/bin/mpv",
                "--no-video",
                "--really-quiet",
                "--",
                "https://example.test/live.mp3",
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.assertTrue(player.is_playing)

    @patch("hardware_io.audio.mpv_streaming_audio_player.subprocess.Popen")
    @patch("hardware_io.audio.mpv_streaming_audio_player.shutil.which")
    def test_play_replaces_existing_process(self, which: Mock, popen: Mock) -> None:
        which.return_value = "/usr/bin/mpv"
        first = Mock()
        first.poll.return_value = None
        second = Mock()
        second.poll.return_value = None
        popen.side_effect = [first, second]
        player = MpvStreamingAudioPlayer()

        player.play("https://example.test/one")
        player.play("https://example.test/two")

        first.terminate.assert_called_once_with()
        first.wait.assert_called_once_with(timeout=3.0)
        self.assertTrue(player.is_playing)

    @patch("hardware_io.audio.mpv_streaming_audio_player.shutil.which")
    def test_missing_mpv_reports_clear_error(self, which: Mock) -> None:
        which.return_value = None
        player = MpvStreamingAudioPlayer()

        with self.assertRaisesRegex(RuntimeError, "mpv executable not found"):
            player.play("https://example.test/live")

    @patch("hardware_io.audio.mpv_streaming_audio_player.subprocess.Popen")
    @patch("hardware_io.audio.mpv_streaming_audio_player.shutil.which")
    def test_stop_kills_process_after_timeout(self, which: Mock, popen: Mock) -> None:
        which.return_value = "/usr/bin/mpv"
        process = Mock()
        process.poll.return_value = None
        process.wait.side_effect = [subprocess.TimeoutExpired("mpv", 1.0), 0]
        popen.return_value = process
        player = MpvStreamingAudioPlayer(stop_timeout_s=1.0)
        player.play("https://example.test/live")

        player.stop()

        process.terminate.assert_called_once_with()
        process.kill.assert_called_once_with()
        self.assertFalse(player.is_playing)


if __name__ == "__main__":
    unittest.main()
