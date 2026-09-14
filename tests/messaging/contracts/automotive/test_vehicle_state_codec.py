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
        state = VehicleState(
            timestamp=self.timestamp,
            engine_speed_rad_s=2.0 * math.pi,
            vehicle_speed_m_s=4.4704,
            transmission_gear=3,
            throttle_position=0.25,
            commanded_throttle_position=0.3,
            accelerator_pedal_position=0.5,
            engine_load=0.75,
            absolute_engine_load=0.8,
            fuel_system_status_1=2,
            fuel_system_status_2=0,
            short_term_fuel_trim_bank1=0.05,
            long_term_fuel_trim_bank1=-0.02,
            ignition_timing_advance_deg=12.5,
            intake_manifold_pressure_pa=100_000.0,
            barometric_pressure_pa=101_000.0,
            boost_pressure_pa=6894.757293168,
            mass_air_flow_kg_s=0.02,
            coolant_temperature_k=273.15,
            intake_air_temperature_k=373.15,
            fuel_level=0.4,
            fuel_rail_pressure_pa=3_120_000.0,
            commanded_equivalence_ratio=0.92,
            measured_equivalence_ratio=0.94,
            engine_fuel_rate_m3_s=2.0e-6,
            control_voltage_v=14.2,
        )
        payload = encode_vehicle_state(state)
        data = payload["data"]

        self.assertAlmostEqual(data["engine_speed_rad_s"], 2.0 * math.pi)
        self.assertAlmostEqual(data["vehicle_speed_m_s"], 4.4704)
        self.assertEqual(data["transmission_gear"], 3)
        self.assertEqual(data["throttle_position"], 0.25)
        self.assertEqual(data["commanded_throttle_position"], 0.3)
        self.assertEqual(data["accelerator_pedal_position"], 0.5)
        self.assertEqual(data["engine_load"], 0.75)
        self.assertEqual(data["absolute_engine_load"], 0.8)
        self.assertEqual(data["short_term_fuel_trim_bank1"], 0.05)
        self.assertEqual(data["long_term_fuel_trim_bank1"], -0.02)
        self.assertEqual(data["ignition_timing_advance_deg"], 12.5)
        self.assertEqual(data["intake_manifold_pressure_pa"], 100_000.0)
        self.assertEqual(data["barometric_pressure_pa"], 101_000.0)
        self.assertAlmostEqual(data["boost_pressure_pa"], 6894.757293168)
        self.assertEqual(data["mass_air_flow_kg_s"], 0.02)
        self.assertAlmostEqual(data["coolant_temperature_k"], 273.15)
        self.assertAlmostEqual(data["intake_air_temperature_k"], 373.15)
        self.assertEqual(data["fuel_level"], 0.4)
        self.assertEqual(data["fuel_rail_pressure_pa"], 3_120_000.0)
        self.assertEqual(data["commanded_equivalence_ratio"], 0.92)
        self.assertEqual(data["measured_equivalence_ratio"], 0.94)
        self.assertEqual(data["engine_fuel_rate_m3_s"], 2.0e-6)
        self.assertEqual(data["control_voltage_v"], 14.2)

    def test_absolute_engine_load_may_exceed_one(self) -> None:
        payload = encode_vehicle_state(
            VehicleState(
                timestamp=self.timestamp,
                absolute_engine_load=1.35,
            )
        )
        self.assertEqual(payload["data"]["absolute_engine_load"], 1.35)

    def test_all_data_fields_are_present_and_nullable(self) -> None:
        payload = encode_vehicle_state(VehicleState(timestamp=self.timestamp))
        expected_fields = {
            "engine_speed_rad_s", "vehicle_speed_m_s", "transmission_gear",
            "throttle_position", "commanded_throttle_position",
            "accelerator_pedal_position", "engine_load", "absolute_engine_load",
            "fuel_system_status_1", "fuel_system_status_2",
            "short_term_fuel_trim_bank1", "long_term_fuel_trim_bank1",
            "ignition_timing_advance_deg",
            "intake_manifold_pressure_pa", "barometric_pressure_pa",
            "boost_pressure_pa", "mass_air_flow_kg_s", "coolant_temperature_k",
            "intake_air_temperature_k", "fuel_level", "fuel_rail_pressure_pa",
            "commanded_equivalence_ratio", "measured_equivalence_ratio",
            "engine_fuel_rate_m3_s", "control_voltage_v",
        }
        self.assertEqual(set(payload["data"]), expected_fields)
        self.assertTrue(all(value is None for value in payload["data"].values()))

    def test_envelope_is_versioned_and_contains_source_and_timestamp(self) -> None:
        payload = encode_vehicle_state(
            VehicleState(timestamp=self.timestamp), source="simulator"
        )
        self.assertEqual(payload["version"], 4)
        self.assertEqual(payload["source"], "simulator")
        self.assertEqual(payload["timestamp"]["nanoseconds"], 123_456_000)
        self.assertIsInstance(payload["timestamp"]["seconds"], int)

    def test_decoder_accepts_legacy_v2_payload(self) -> None:
        from messaging.contracts.automotive.vehicle_state_decoder import decode_vehicle_state

        payload = encode_vehicle_state(
            VehicleState(timestamp=self.timestamp, vehicle_speed_m_s=12.0),
            source="legacy-v2",
        )
        payload["version"] = 2
        for field in (
            "commanded_throttle_position",
            "absolute_engine_load",
            "fuel_system_status_1",
            "fuel_system_status_2",
            "short_term_fuel_trim_bank1",
            "long_term_fuel_trim_bank1",
            "ignition_timing_advance_deg",
            "fuel_rail_pressure_pa",
            "measured_equivalence_ratio",
        ):
            payload["data"].pop(field)
        payload["data"].pop("commanded_equivalence_ratio")

        message = decode_vehicle_state(payload)

        self.assertEqual(message.version, 2)
        self.assertIsNone(message.data.commanded_equivalence_ratio)

    def test_decoder_accepts_legacy_v1_payload(self) -> None:
        from messaging.contracts.automotive.vehicle_state_decoder import decode_vehicle_state

        payload = encode_vehicle_state(
            VehicleState(timestamp=self.timestamp, vehicle_speed_m_s=12.0),
            source="legacy-test",
        )
        payload["version"] = 1
        for field in (
            "commanded_throttle_position",
            "absolute_engine_load",
            "fuel_system_status_1",
            "fuel_system_status_2",
            "short_term_fuel_trim_bank1",
            "long_term_fuel_trim_bank1",
            "ignition_timing_advance_deg",
            "fuel_rail_pressure_pa",
            "measured_equivalence_ratio",
        ):
            payload["data"].pop(field)
        payload["data"].pop("engine_fuel_rate_m3_s")
        payload["data"].pop("commanded_equivalence_ratio")

        message = decode_vehicle_state(payload)

        self.assertEqual(message.version, 1)
        self.assertEqual(message.data.vehicle_speed_m_s, 12.0)
        self.assertIsNone(message.data.engine_fuel_rate_m3_s)

    def test_decoder_accepts_legacy_v3_payload(self) -> None:
        from messaging.contracts.automotive.vehicle_state_decoder import decode_vehicle_state

        payload = encode_vehicle_state(
            VehicleState(timestamp=self.timestamp, commanded_equivalence_ratio=1.0),
            source="legacy-v3",
        )
        payload["version"] = 3
        for field in (
            "commanded_throttle_position",
            "absolute_engine_load",
            "fuel_system_status_1",
            "fuel_system_status_2",
            "short_term_fuel_trim_bank1",
            "long_term_fuel_trim_bank1",
            "ignition_timing_advance_deg",
            "fuel_rail_pressure_pa",
            "measured_equivalence_ratio",
        ):
            payload["data"].pop(field)

        message = decode_vehicle_state(payload)
        self.assertEqual(message.version, 3)
        self.assertIsNone(message.data.measured_equivalence_ratio)


if __name__ == "__main__":
    unittest.main()
