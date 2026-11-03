# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Verify captured-IQ warmup and audio prebuffer configuration."""

import unittest

from controllers.radio.native_radio_service import NativeRadioService
from hardware_io.audio.pcm_playback_worker import PcmPlaybackWorker


class _Receiver:
    def __init__(self):
        self.resets = 0

    def reset(self):
        self.resets += 1


class _Block:
    def __init__(self):
        self.samples = bytes(200)
        self.sample_rate_hz = 1000
        self.center_frequency_hz = 104300000


class _Source:
    def __init__(self):
        self.reads = 0
        self.closed = False

    def open(self): pass
    def set_sample_rate(self, rate): pass
    def set_gain(self, gain): pass
    def set_center_frequency(self, freq): pass
    def start(self): pass
    def stop(self): pass
    def close(self): self.closed = True

    def read_iq(self):
        self.reads += 1
        return _Block()


class WarmupTest(unittest.TestCase):
    def test_rf_warmup_consumes_samples_without_dsp_processing(self):
        source = _Source()
        receiver = _Receiver()
        service = NativeRadioService(source, receiver,
                                     center_frequency_hz=104300000,
                                     sample_rate_hz=1000,
                                     rf_warmup_seconds=0.25)
        service.start()
        self.assertEqual(source.reads, 3)
        self.assertEqual(service.warmup_iq_samples, 300)
        self.assertEqual(service.status.processed_blocks, 0)
        self.assertGreaterEqual(receiver.resets, 2)
        service.stop()

    def test_negative_warmup_rejected(self):
        with self.assertRaises(ValueError):
            NativeRadioService(_Source(), _Receiver(),
                               center_frequency_hz=104300000,
                               rf_warmup_seconds=-1)

    def test_audio_prebuffer_validation(self):
        with self.assertRaises(ValueError):
            PcmPlaybackWorker(object(), prebuffer_ms=-1)


if __name__ == "__main__":
    unittest.main()
