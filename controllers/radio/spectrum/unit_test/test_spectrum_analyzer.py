# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for complex RF FFT frequency mapping."""

import unittest

import numpy as np

from controllers.radio.spectrum.spectrum_analyzer import SpectrumAnalyzer
from hardware_io.sdr import IqBlock


class SpectrumAnalyzerTest(unittest.TestCase):
    def test_tone_maps_to_positive_frequency_offset(self) -> None:
        sample_rate = 2_048_000
        fft_size = 2048
        offset_bins = 128
        phases = 2 * np.pi * offset_bins * np.arange(fft_size) / fft_size
        iq = 127.5 + 55 * np.column_stack((np.cos(phases), np.sin(phases)))
        block = IqBlock(
            samples=np.clip(iq, 0, 255).astype(np.uint8).tobytes(),
            center_frequency_hz=104_300_000,
            sample_rate_hz=sample_rate,
            timestamp_ns=123,
        )

        frame = SpectrumAnalyzer(fft_size).analyze(block)

        peak = int(np.argmax(frame.power_db))
        self.assertEqual(peak, fft_size // 2 + offset_bins)
        self.assertEqual(frame.bin_width_hz, 1000)
        self.assertEqual(frame.timestamp_ns, 123)

    def test_invalid_block_is_rejected(self) -> None:
        block = IqBlock(
            samples=b"\x00\x01\x02",
            center_frequency_hz=100_000_000,
            sample_rate_hz=2_400_000,
            timestamp_ns=1,
        )
        with self.assertRaises(ValueError):
            SpectrumAnalyzer().analyze(block)

    def test_fft_size_must_be_power_of_two(self) -> None:
        with self.assertRaises(ValueError):
            SpectrumAnalyzer(1000)


if __name__ == "__main__":
    unittest.main()
