"""Tests for radio terminal formatting."""

import unittest

from frontends.tui.radio.radio_dashboard_view import format_frequency


class RadioDashboardViewTest(unittest.TestCase):
    def test_formats_common_radio_frequencies(self) -> None:
        self.assertEqual(format_frequency(101_100_000), "101.1 MHz")
        self.assertEqual(format_frequency(162_550_000), "162.55 MHz")
        self.assertEqual(format_frequency(800_000), "800 kHz")
