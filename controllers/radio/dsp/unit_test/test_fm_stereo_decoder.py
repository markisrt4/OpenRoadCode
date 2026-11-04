# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Synthetic FM stereo tests; no SDR or sound device required."""

import unittest

import numpy as np

from controllers.radio.dsp.fm_stereo_decoder import FmStereoDecoder


RATE = 240_000


def stereo_multiplex(count=120_000, pilot=0.1):
    t = np.arange(count) / RATE
    left = 0.25 * np.sin(2 * np.pi * 1_000 * t)
    right = 0.25 * np.sin(2 * np.pi * 2_000 * t)
    return ((left + right) + (left - right) * np.cos(2 * np.pi * 38_000 * t)
            + pilot * np.sin(2 * np.pi * 19_000 * t)).astype(np.float32)


class FmStereoDecoderTest(unittest.TestCase):
    def test_recovers_separate_channels(self):
        decoder = FmStereoDecoder()
        pcm = decoder.process(stereo_multiplex())
        self.assertEqual(pcm.shape, (24_000, 2))
        self.assertTrue(decoder.stereo_locked)
        for channel, expected in ((0, 1_000), (1, 2_000)):
            audio = pcm[8_000:, channel]
            spectrum = np.abs(np.fft.rfft(audio))
            frequencies = np.fft.rfftfreq(len(audio), 1 / 48_000)
            self.assertLess(abs(frequencies[np.argmax(spectrum)] - expected), 10)

    def test_missing_pilot_falls_back_to_mono(self):
        decoder = FmStereoDecoder()
        pcm = decoder.process(stereo_multiplex(pilot=0))
        self.assertFalse(decoder.stereo_locked)
        np.testing.assert_allclose(pcm[:, 0], pcm[:, 1], atol=1e-6)

    def test_rejects_non_vector(self):
        with self.assertRaises(ValueError):
            FmStereoDecoder().process(np.zeros((10, 2)))


if __name__ == "__main__":
    unittest.main()
