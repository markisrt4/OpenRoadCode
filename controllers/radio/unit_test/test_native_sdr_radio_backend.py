# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Hardware-free contract tests for native SDR tuner control."""

import unittest
from unittest.mock import create_autospec

from controllers.radio.adapters.native_sdr_radio_backend import NativeSdrRadioBackend
from controllers.radio.radio_controller import RadioController
from controllers.radio.radio_types import RadioMode, RadioRange
from hardware_io.sdr.sdr_source_if import SdrSourceIf


class NativeSdrRadioBackendTest(unittest.TestCase):
    def setUp(self) -> None:
        self.source = create_autospec(SdrSourceIf, instance=True)
        self.backend = NativeSdrRadioBackend(self.source)

    def test_start_tune_stop_and_idempotence(self) -> None:
        self.backend.start()
        self.backend.start()
        self.source.open.assert_called_once_with()
        self.source.set_sample_rate.assert_called_once_with(2_400_000)
        self.source.set_gain.assert_called_once_with(30.0)
        self.source.set_center_frequency.assert_called_once_with(104_300_000)
        self.source.start.assert_called_once_with()
        self.backend.set_frequency(104_700_000)
        self.source.set_center_frequency.assert_called_with(104_700_000)
        self.backend.stop()
        self.backend.stop()
        self.source.stop.assert_called_once_with()
        self.source.close.assert_called_once_with()

    def test_failed_start_releases_source(self) -> None:
        self.source.start.side_effect = RuntimeError("USB disconnected")
        with self.assertRaisesRegex(RuntimeError, "USB disconnected"):
            self.backend.start()
        self.source.close.assert_called_once_with()

    def test_rejects_invalid_mode_and_frequency(self) -> None:
        with self.assertRaises(ValueError):
            self.backend.set_mode("SSB", 3000)
        with self.assertRaises(ValueError):
            self.backend.set_mode("AM", 0)
        with self.assertRaises(ValueError):
            self.backend.set_frequency(0)

    def test_controller_contract_without_ui(self) -> None:
        mode = RadioMode("WFM", 200_000, 200_000)
        controller = RadioController(
            backend=self.backend,
            presets=[],
            default_mode=mode,
            radio_range=RadioRange(88_000_000, 108_000_000, 104_300_000),
        )
        self.assertEqual(controller.start(), 104_300_000)
        self.assertEqual(controller.frequency_up(), 104_500_000)
        self.assertEqual(controller.get_snr(), None)
        self.assertEqual(controller.get_rds(), None)
        controller.stop()


if __name__ == "__main__":
    unittest.main()
