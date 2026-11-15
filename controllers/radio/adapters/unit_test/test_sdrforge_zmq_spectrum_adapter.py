# SPDX-License-Identifier: MIT
"""Hardware-free contract tests for SDRForge spectrum telemetry."""
from __future__ import annotations

import unittest

from controllers.radio.adapters.sdrforge_zmq_spectrum_adapter import (
    SdrForgeTelemetrySubscriber, spectrum_bins,
)
from ui.radio.sdrforge_spectrum_if import SpectrumPresentation


class SpectrumContractTest(unittest.TestCase):
    def test_immutable_validated_snapshot(self) -> None:
        snapshot = SpectrumPresentation((0.0, 0.5, 1.0))
        self.assertEqual(snapshot.bins[1], 0.5)
        with self.assertRaises(ValueError):
            SpectrumPresentation((1.1,))
        with self.assertRaises(ValueError):
            SpectrumPresentation(())
        with self.assertRaises(AttributeError):
            snapshot.bins = (0.2,)

    def test_real_sdrforge_power_db_contract(self) -> None:
        bins = spectrum_bins("spectrum", {"power_db": [-90, -50, -10]})
        self.assertEqual(bins, (0.0, 0.5, 1.0))

    def test_malformed_spectrum_is_ignored(self) -> None:
        self.assertIsNone(spectrum_bins("receiver", {"power_db": [0, 1]}))
        self.assertIsNone(spectrum_bins("spectrum", {"power_db": []}))
        self.assertIsNone(spectrum_bins("spectrum", {"power_db": ["oops"]}))
        self.assertIsNone(spectrum_bins("spectrum", {"power_db": [float("nan")]}))
        self.assertIsNone(spectrum_bins("spectrum", {"power_db": [float("inf")]}))
        self.assertIsNone(spectrum_bins("spectrum", {"power_db": ["-inf"]}))

    def test_subscriber_empty_and_idempotent_close(self) -> None:
        source = SdrForgeTelemetrySubscriber()
        self.assertIsNone(source.latest_spectrum())
        source.close()
        source.close()
        with self.assertRaises(RuntimeError):
            source.start()


if __name__ == "__main__":
    unittest.main()
