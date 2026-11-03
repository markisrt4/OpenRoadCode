# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Fake-source tests for the live SDR service without attached hardware."""

import unittest
from unittest.mock import Mock

import numpy as np

from controllers.radio.native_radio_service import NativeRadioService
from hardware_io.sdr.sdr_types import IqBlock


class NativeRadioServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.source = Mock()
        self.receiver = Mock()
        self.receiver.process.return_value = {
            "fm": np.zeros(480, dtype=np.float32),
            "weather": np.ones(480, dtype=np.float32),
        }
        self.source.read_iq.return_value = IqBlock(
            bytes([128, 128]) * 2400, 104_300_000, 2_400_000, 1_000_000_000
        )
        self.source.get_acquisition_stats.return_value = {"dropped_blocks": 0}
        self.delivered = []
        self.service = NativeRadioService(
            self.source, self.receiver, center_frequency_hz=104_300_000,
            pcm_sink=lambda name, pcm: self.delivered.append((name, pcm))
        )

    def test_start_process_stop(self) -> None:
        self.service.start()
        pcm = self.service.process_once()
        self.assertEqual(set(pcm), {"fm", "weather"})
        self.assertEqual([name for name, _ in self.delivered], ["fm", "weather"])
        self.assertEqual(self.service.status.processed_iq_samples, 2400)
        self.service.stop()
        self.source.open.assert_called_once_with()
        self.source.start.assert_called_once_with()
        self.source.stop.assert_called_once_with()
        self.source.close.assert_called_once_with()

    def test_gap_resets_dsp(self) -> None:
        self.service.start()
        self.service.process_once()
        self.source.read_iq.return_value = IqBlock(
            bytes([128, 128]) * 2400, 104_300_000, 2_400_000, 1_100_000_000
        )
        self.service.process_once()
        self.assertEqual(self.service.status.discontinuities, 1)
        self.assertEqual(self.receiver.reset.call_count, 2)

    def test_dropped_blocks_reset_dsp(self) -> None:
        self.service.start()
        self.service.process_once()
        self.source.get_acquisition_stats.return_value = {"dropped_blocks": 2}
        self.service.process_once()
        self.assertEqual(self.service.status.discontinuities, 1)

    def test_start_failure_closes_device(self) -> None:
        self.source.start.side_effect = RuntimeError("USB unavailable")
        with self.assertRaisesRegex(RuntimeError, "USB unavailable"):
            self.service.start()
        self.source.close.assert_called_once_with()
        self.assertFalse(self.service.status.started)

    def test_processing_requires_start(self) -> None:
        with self.assertRaises(RuntimeError):
            self.service.process_once()


if __name__ == "__main__":
    unittest.main()
