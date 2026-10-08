# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Unit tests for hardware-independent SDR types."""

import unittest

from hardware_io.sdr import IqBlock, IqSampleFormat, SdrCapabilities, SdrSourceIf


class SdrTypesTest(unittest.TestCase):
    def test_iq_block_defaults_to_rtl_sdr_compatible_u8_interleaved(self) -> None:
        block = IqBlock(
            samples=b"\x00\xff\x7f\x80",
            center_frequency_hz=104_300_000,
            sample_rate_hz=2_400_000,
            timestamp_ns=123456789,
        )

        self.assertEqual(block.sample_format, IqSampleFormat.U8_INTERLEAVED)
        self.assertEqual(block.samples, b"\x00\xff\x7f\x80")

    def test_capabilities_support_discrete_or_ranged_sample_rates(self) -> None:
        capabilities = SdrCapabilities(
            min_frequency_hz=24_000_000,
            max_frequency_hz=1_766_000_000,
            supported_sample_rates_hz=(1_024_000, 2_048_000, 2_400_000),
            supports_manual_gain=True,
        )

        self.assertIn(2_400_000, capabilities.supported_sample_rates_hz)
        self.assertTrue(capabilities.supports_manual_gain)

    def test_source_interface_remains_abstract(self) -> None:
        with self.assertRaises(TypeError):
            SdrSourceIf()


if __name__ == "__main__":
    unittest.main()
