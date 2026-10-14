# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Synthetic streaming FM audio smoke tests."""

import unittest

import numpy as np

from controllers.radio.dsp.wbfm_mono_demodulator import WbfmMonoDemodulator
from hardware_io.sdr import IqBlock


class WbfmMonoDemodulatorTest(unittest.TestCase):
    def test_output_rate_and_nonzero_tone(self) -> None:
        demodulator = WbfmMonoDemodulator()
        rate = 2_400_000
        tone_hz = 1000
        count = 240_000
        t = np.arange(count) / rate
        phase = 25_000 / tone_hz * (1 - np.cos(2 * np.pi * tone_hz * t))
        iq = np.exp(1j * phase)
        packed = np.empty(count * 2, dtype=np.uint8)
        packed[::2] = np.clip(np.rint(127.5 + 100 * iq.real), 0, 255).astype(np.uint8)
        packed[1::2] = np.clip(np.rint(127.5 + 100 * iq.imag), 0, 255).astype(np.uint8)
        output = []
        for chunk in np.array_split(packed, 10):
            output.append(demodulator.process(
                IqBlock(chunk.tobytes(), 104_300_000, rate, 1)
            ))
        audio = np.concatenate(output)
        self.assertEqual(len(audio), 4800)
        self.assertGreater(float(np.std(audio[1000:])), 0.001)
        spectrum = np.abs(np.fft.rfft(audio[1000:]))
        freqs = np.fft.rfftfreq(len(audio[1000:]), 1 / 48_000)
        self.assertLess(abs(freqs[int(np.argmax(spectrum))] - tone_hz), 20)

    def test_rejects_invalid_rate(self) -> None:
        with self.assertRaises(ValueError):
            WbfmMonoDemodulator(sample_rate_hz=1_000_000)


if __name__ == "__main__":
    unittest.main()
