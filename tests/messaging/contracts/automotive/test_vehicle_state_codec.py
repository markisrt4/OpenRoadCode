# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from datetime import datetime, timezone
import math
import unittest

from controllers.automotive.vehicle_state import VehicleState
from messaging.contracts.automotive.vehicle_state_codec import encode_vehicle_state


class VehicleStateCodecTest(unittest.TestCase):
    def setUp(self) -> None:
        self.timestamp = datetime(
            2026, 8, 21, 17, 27, 14, 123456, tzinfo=timezone.utc
        )

    def test_encodes_strict_si_units(self) -> None:
        payload = encode_vehicle_state(
            VehicleState(
                timestamp=self.timestamp,
                rpm=60.0,
                speed_mph=10.0,
                throttle_pct=25.0,
                accelerator_pedal_pct=50.0,
                engine_load_pct=75.0,
                map_kpa=100,
                baro_kpa=101,
                boost_psi=1.0,
                maf_gps=20.0,
                coolant_temp_f=32.0,
                intake_temp_f=212.0,
                fuel_level_pct=40.0,
                control_voltage=14.2,
            )
        )
        data = payload["data"]

        self.assertAlmostEqual(data["engine_speed_rad_s"], 2.0 * math.pi)
        self.assertAlmostEqual(data["vehicle_speed_m_s"], 4.4704)
        self.assertEqual(data["throttle_position"], 0.25)
        self.assertEqual(data["accelerator_pedal_position"], 0.5)
        self.assertEqual(data["engine_load"], 0.75)
        self.assertEqual(data["intake_manifold_pressure_pa"], 100_000)
        self.assertEqual(data["barometric_pressure_pa"], 101_000)
        self.assertAlmostEqual(data["boost_pressure_pa"], 6894.757293168)
        self.assertEqual(data["mass_air_flow_kg_s"], 0.02)
        self.assertAlmostEqual(data["coolant_temperature_k"], 273.15)
        self.assertAlmostEqual(data["intake_air_temperature_k"], 373.15)
        self.assertEqual(data["fuel_level"], 0.4)
        self.assertEqual(data["control_voltage_v"], 14.2)

    def test_all_data_fields_are_present_and_nullable(self) -> None:
        payload = encode_vehicle_state(VehicleState(timestamp=self.timestamp))
        expected_fields = {
            "engine_speed_rad_s",
            "vehicle_speed_m_s",
            "throttle_position",
            "accelerator_pedal_position",
            "engine_load",
            "intake_manifold_pressure_pa",
            "barometric_pressure_pa",
            "boost_pressure_pa",
            "mass_air_flow_kg_s",
            "coolant_temperature_k",
            "intake_air_temperature_k",
            "fuel_level",
            "control_voltage_v",
        }
        self.assertEqual(set(payload["data"]), expected_fields)
        self.assertTrue(all(value is None for value in payload["data"].values()))

    def test_envelope_is_versioned_and_contains_source_and_timestamp(self) -> None:
        payload = encode_vehicle_state(
            VehicleState(timestamp=self.timestamp),
            source="simulator",
        )
        self.assertEqual(payload["version"], 1)
        self.assertEqual(payload["source"], "simulator")
        self.assertEqual(payload["timestamp"]["nanoseconds"], 123_456_000)
        self.assertIsInstance(payload["timestamp"]["seconds"], int)


if __name__ == "__main__":
    unittest.main()
