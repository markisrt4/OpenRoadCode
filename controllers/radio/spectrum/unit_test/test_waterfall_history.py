# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Unit tests for bounded native SDR waterfall history."""

import unittest

from controllers.radio.spectrum.spectrum_analyzer import SpectrumFrame
from controllers.radio.spectrum.waterfall_history import WaterfallHistory


def spectrum(values: tuple[float, ...], center: int = 104_100_000) -> SpectrumFrame:
    return SpectrumFrame(center, 2_400_000, 1200.0, values, 1)


class WaterfallHistoryTest(unittest.TestCase):
    def test_newest_row_first_and_bounded(self) -> None:
        history = WaterfallHistory(rows=2, min_db=-100, max_db=0)
        history.append(spectrum((-80.0, -20.0)))
        history.append(spectrum((-60.0, -40.0)))
        history.append(spectrum((-10.0, -90.0)))
        image = history.image()
        self.assertEqual(image.shape, (2, 2))
        self.assertAlmostEqual(float(image[0, 0]), 0.9)
        self.assertAlmostEqual(float(image[1, 0]), 0.4)

    def test_retune_resets_history(self) -> None:
        history = WaterfallHistory(rows=3, min_db=-100, max_db=0)
        history.append(spectrum((-10.0,)))
        history.append(spectrum((-80.0,), center=105_000_000))
        image = history.image()
        self.assertAlmostEqual(float(image[0, 0]), 0.2)
        self.assertAlmostEqual(float(image[1, 0]), 0.0)

    def test_clipping(self) -> None:
        history = WaterfallHistory(rows=1, min_db=-80, max_db=-20)
        history.append(spectrum((-100.0, -10.0)))
        self.assertEqual(history.image().tolist(), [[0.0, 1.0]])

    def test_invalid_range(self) -> None:
        with self.assertRaises(ValueError):
            WaterfallHistory(min_db=-10, max_db=-80)


if __name__ == "__main__":
    unittest.main()
