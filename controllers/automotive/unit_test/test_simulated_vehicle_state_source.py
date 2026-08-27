# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for hardware-free vehicle telemetry simulation."""

import unittest

from controllers.automotive import SimulatedVehicleStateSource


class SimulatedVehicleStateSourceTest(unittest.TestCase):
    def test_requires_connection(self) -> None:
        source = SimulatedVehicleStateSource()

        with self.assertRaises(RuntimeError):
            source.read_state()

    def test_connected_source_generates_changing_complete_state(self) -> None:
        source = SimulatedVehicleStateSource()
        source.connect()

        first = source.read_state()
        second = source.read_state()

        self.assertNotEqual(first.engine_speed_rad_s, second.engine_speed_rad_s)
        self.assertIsNotNone(first.vehicle_speed_m_s)
        self.assertIsNotNone(first.coolant_temperature_k)
        self.assertIsNotNone(first.control_voltage_v)

        source.disconnect()
        with self.assertRaises(RuntimeError):
            source.read_state()
