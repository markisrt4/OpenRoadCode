# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Contract tests for optional SDRForge/SDR++ rigctl telemetry."""

from __future__ import annotations

import unittest
from unittest.mock import Mock

from controllers.radio.adapters.rigctl_radio_backend import RigctlRadioBackend


class RigctlRadioTelemetryTest(unittest.TestCase):
    def test_unsupported_levels_are_not_displayed_as_measurements(self) -> None:
        client = Mock()
        client.get_signal_strength.return_value = "RPRT -11"
        client.get_snr.return_value = "RPRT -1"
        client.get_rds.return_value = "RPRT -11"
        backend = RigctlRadioBackend(client)

        self.assertIsNone(backend.get_signal_strength())
        self.assertIsNone(backend.get_snr())
        self.assertIsNone(backend.get_rds())

    def test_supported_values_are_preserved(self) -> None:
        client = Mock()
        client.get_signal_strength.return_value = " -42.5\n"
        client.get_snr.return_value = " 19.2 "
        client.get_rds.return_value = " Station name "
        backend = RigctlRadioBackend(client)

        self.assertEqual(backend.get_signal_strength(), "-42.5")
        self.assertEqual(backend.get_snr(), "19.2")
        self.assertEqual(backend.get_rds(), "Station name")

    def test_empty_telemetry_is_unavailable(self) -> None:
        client = Mock()
        client.get_signal_strength.return_value = ""
        client.get_snr.return_value = "   "
        client.get_rds.return_value = None
        backend = RigctlRadioBackend(client)

        self.assertIsNone(backend.get_signal_strength())
        self.assertIsNone(backend.get_snr())
        self.assertIsNone(backend.get_rds())


if __name__ == "__main__":
    unittest.main()
