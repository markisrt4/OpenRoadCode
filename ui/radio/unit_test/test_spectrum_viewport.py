# SPDX-License-Identifier: MIT
"""Contract tests for the transport-independent RF viewport."""

import unittest

from ui.radio.sdrforge_spectrum_if import SpectrumViewport


class SpectrumViewportTest(unittest.TestCase):
    def test_frequency_mapping(self):
        viewport = SpectrumViewport(90_900_000, 2_400_000)
        self.assertEqual(viewport.frequency_at(0), 89_700_000)
        self.assertEqual(viewport.frequency_at(0.5), 90_900_000)
        self.assertEqual(viewport.frequency_at(1), 92_100_000)

    def test_pan_preserves_span_and_recenter_setting(self):
        viewport = SpectrumViewport(90_900_000, 2_400_000, False)
        moved = viewport.pan(0.25)
        self.assertEqual(moved.center_hz, 91_500_000)
        self.assertEqual(moved.span_hz, viewport.span_hz)
        self.assertFalse(moved.recenter_on_tune)
        self.assertEqual(viewport.center_hz, 90_900_000)

    def test_zoom_preserves_center_and_clamps(self):
        viewport = SpectrumViewport(90_900_000, 2_400_000)
        self.assertEqual(viewport.zoom(0.5).span_hz, 1_200_000)
        self.assertEqual(viewport.zoom(0.001).span_hz, 100_000)
        self.assertEqual(viewport.zoom(10, max_span_hz=2_400_000).span_hz, 2_400_000)
        self.assertEqual(viewport.zoom(0.5).center_hz, viewport.center_hz)

    def test_invalid_zoom(self):
        viewport = SpectrumViewport(90_900_000, 2_400_000)
        with self.assertRaises(ValueError):
            viewport.zoom(0)


if __name__ == "__main__":
    unittest.main()
