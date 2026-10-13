# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Unit tests for RF spectrum display processing."""

import unittest

from controllers.radio.spectrum.spectrum_analyzer import SpectrumFrame
from controllers.radio.spectrum.spectrum_display_processor import SpectrumDisplayProcessor


def frame(values: tuple[float, ...], center: int = 100_000_000) -> SpectrumFrame:
    return SpectrumFrame(center, 2_400_000, 1_200_000, values, 123)


class SpectrumDisplayProcessorTest(unittest.TestCase):
    def test_exponential_smoothing_and_peak_hold(self) -> None:
        processor = SpectrumDisplayProcessor(alpha=0.25)
        processor.process(frame((-40.0, -50.0)))
        result = processor.process(frame((-20.0, -70.0)))
        self.assertEqual(result.smoothed_db, (-35.0, -55.0))
        self.assertEqual(result.peak_db, (-35.0, -50.0))

    def test_peak_reset_preserves_smoothing(self) -> None:
        processor = SpectrumDisplayProcessor(alpha=0.5)
        processor.process(frame((-40.0,)))
        processor.process(frame((-20.0,)))
        processor.reset_peaks()
        result = processor.process(frame((-50.0,)))
        self.assertEqual(result.smoothed_db, (-40.0,))
        self.assertEqual(result.peak_db, (-40.0,))

    def test_retune_resets_display_history(self) -> None:
        processor = SpectrumDisplayProcessor(alpha=0.1)
        processor.process(frame((-10.0,), center=100_000_000))
        result = processor.process(frame((-70.0,), center=100_200_000))
        self.assertEqual(result.smoothed_db, (-70.0,))
        self.assertEqual(result.peak_db, (-70.0,))

    def test_invalid_alpha_is_rejected(self) -> None:
        for alpha in (-0.1, 0.0, 1.1):
            with self.subTest(alpha=alpha), self.assertRaises(ValueError):
                SpectrumDisplayProcessor(alpha=alpha)


if __name__ == "__main__":
    unittest.main()
