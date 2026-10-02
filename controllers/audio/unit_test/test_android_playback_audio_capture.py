# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Regression tests for the Android playback capture transport."""
import io
import struct
import threading
import unittest
from unittest.mock import patch

import numpy as np

from controllers.audio.capture.android_playback_audio_capture import AndroidPlaybackAudioCapture
from controllers.audio.music_analysis.music_analysis_session import MusicAnalysisSession


class _ShortReadStream(io.BytesIO):
    def __init__(self, data):
        super().__init__(data)
        self.closed_event = threading.Event()

    def read(self, size=-1):
        return super().read(min(size, 3) if size >= 0 else 3)

    def close(self):
        self.closed_event.set()
        super().close()


def _stream(samples, rate=48000, channels=1, magic=b"ORCA"):
    return _ShortReadStream(struct.pack("<4sII", magic, rate, channels)
                            + np.asarray(samples, dtype="<i2").tobytes())


class AndroidPlaybackAudioCaptureTest(unittest.TestCase):
    def test_accumulates_short_reads_and_preserves_pcm_values(self):
        stream = _stream([0, -32768, 16384, 32767, 100, -100, 200, -200])
        frames = []
        done = threading.Event()
        capture = AndroidPlaybackAudioCapture(block_size=4)
        def receive(samples, rate):
            frames.append((samples.copy(), rate))
            if len(frames) == 2:
                done.set()
        with patch("controllers.audio.capture.android_playback_audio_capture.urlopen", return_value=stream):
            capture.start(receive)
            self.assertTrue(done.wait(2))
            capture.stop()
        self.assertEqual(len(frames), 2)
        self.assertEqual([rate for _, rate in frames], [48000, 48000])
        np.testing.assert_allclose(frames[0][0], [0, -1, .5, 32767 / 32768])
        np.testing.assert_allclose(frames[1][0], np.array([100, -100, 200, -200]) / 32768)
        self.assertFalse(capture.is_running)
        self.assertTrue(stream.closed_event.is_set())

    def test_rejects_invalid_headers_and_closes_connection(self):
        for stream in (_stream([], magic=b"FAIL"), _stream([], channels=2),
                       _stream([], rate=0), _ShortReadStream(b"ORC")):
            capture = AndroidPlaybackAudioCapture()
            with self.subTest(stream=stream.getvalue()):
                with patch("controllers.audio.capture.android_playback_audio_capture.urlopen", return_value=stream):
                    with self.assertRaises(RuntimeError):
                        capture.start(lambda samples, rate: None)
                self.assertTrue(stream.closed_event.is_set())
                self.assertFalse(capture.is_running)

    def test_restricts_transport_to_loopback(self):
        for url in ("http://192.168.1.5:8768/stream", "https://127.0.0.1:8768/stream",
                    "http://user:password@127.0.0.1:8768/stream"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                AndroidPlaybackAudioCapture(url=url)

    def test_shared_session_uses_same_analyzer_and_calibration(self):
        stream = _stream([0, 1000, -1000, 500] * 512)
        received = threading.Event()
        session = MusicAnalysisSession({"android-playback": lambda: AndroidPlaybackAudioCapture(block_size=2048)},
                                       consumer=lambda state: received.set())
        with patch("controllers.audio.capture.android_playback_audio_capture.urlopen", return_value=stream):
            session.start("android-playback")
            self.assertTrue(received.wait(2))
            state = session.state()
            self.assertEqual(state["source"], "android-playback")
            self.assertEqual(state["sample_rate_hz"], 48000)
            self.assertEqual(len(state["spectrum"]), 24)
            session.stop()
            self.assertFalse(session.state()["running"])


if __name__ == "__main__":
    unittest.main()
