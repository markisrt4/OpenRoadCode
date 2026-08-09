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

        self.assertNotEqual(first.rpm, second.rpm)
        self.assertIsNotNone(first.speed_mph)
        self.assertIsNotNone(first.coolant_temp_f)
        self.assertIsNotNone(first.control_voltage)

        source.disconnect()
        with self.assertRaises(RuntimeError):
            source.read_state()
