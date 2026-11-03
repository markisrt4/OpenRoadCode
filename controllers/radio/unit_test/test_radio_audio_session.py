# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for radio-to-audio lifecycle and PCM routing."""

import unittest
from unittest.mock import Mock

import numpy as np

from controllers.radio.radio_audio_session import RadioAudioSession


class RadioAudioSessionTest(unittest.TestCase):
    def setUp(self):
        self.radio = Mock()
        self.radio.pcm_sink = None
        self.playback = Mock()
        self.session = RadioAudioSession(self.radio, self.playback)

    def test_connects_pcm_and_restores_sink(self):
        original = Mock()
        self.radio.pcm_sink = original
        session = RadioAudioSession(self.radio, self.playback)
        session.select_channel("fm")
        session.start()
        samples = np.ones(128, dtype=np.float32)
        self.radio.pcm_sink("fm", samples)
        original.assert_called_once_with("fm", samples)
        self.playback.submit.assert_called_once_with("fm", samples)
        session.stop()
        self.assertIs(self.radio.pcm_sink, original)
        self.playback.start.assert_called_once_with()
        self.playback.stop.assert_called_once_with()
        self.radio.stop.assert_called_once_with()

    def test_failed_radio_start_closes_audio(self):
        self.radio.start.side_effect = RuntimeError("SDR not found")
        with self.assertRaisesRegex(RuntimeError, "SDR not found"):
            self.session.start()
        self.assertIsNone(self.radio.pcm_sink)
        self.playback.stop.assert_called_once_with()

    def test_requires_start(self):
        with self.assertRaises(RuntimeError):
            self.session.process_once()

    def test_process_delegates_to_service(self):
        self.session.start()
        self.session.process_once()
        self.radio.process_once.assert_called_once_with()
        self.session.stop()


if __name__ == "__main__":
    unittest.main()
