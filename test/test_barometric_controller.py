"""Tests for the barometric controller and BMP3XX adapter."""

from __future__ import annotations

import unittest
from datetime import datetime, timezone

from controllers.environmental import (
    BarometricController,
    BarometricControllerIf,
    BarometricControllerStub,
    BarometricSample,
    BarometricState,
    Bmp3xxBarometricAdapter,
    UnconfiguredBarometricController,
)
from controllers.environmental.component_test.barometric_cli import (
    format_state,
)


class FakeBarometricSource:
    def __init__(
        self,
        sample: BarometricSample = BarometricSample(
            pressure_pa=101_325.0,
            temperature_c=20.0,
        ),
    ) -> None:
        self.sample = sample
        self.connected = False

    @property
    def is_connected(self) -> bool:
        return self.connected

    def connect(self) -> None:
        self.connected = True

    def disconnect(self) -> None:
        self.connected = False

    def read_barometric(self) -> BarometricSample:
        if not self.connected:
            raise RuntimeError("fake sensor is disconnected")
        return self.sample


class FakeBmp3xx:
    def __init__(self) -> None:
        self.is_started = False

    def start(self) -> None:
        self.is_started = True

    def stop(self) -> None:
        self.is_started = False

    def get_pressure_pa(self) -> float:
        return 100_000.0

    def get_temperature_c(self) -> float:
        return 22.5


class BarometricControllerTests(unittest.TestCase):
    def test_implements_controller_interface(self) -> None:
        self.assertTrue(
            issubclass(BarometricController, BarometricControllerIf)
        )

    def test_reads_normalized_sensor_sample(self) -> None:
        sensor = FakeBarometricSource()
        controller = BarometricController(sensor)

        controller.start()
        state = controller.read_state()

        self.assertEqual(state.pressure_pa, 101_325.0)
        self.assertEqual(state.temperature_c, 20.0)
        self.assertAlmostEqual(state.altitude_m, 0.0)
        self.assertAlmostEqual(state.relative_altitude_m, 0.0)
        self.assertEqual(controller.latest_state, state)
        self.assertTrue(controller.is_available)
        self.assertIsNone(controller.status_message)

    def test_start_and_stop_manage_adapter_connection(self) -> None:
        sensor = FakeBarometricSource()
        controller = BarometricController(sensor)

        controller.start()
        self.assertTrue(sensor.connected)
        self.assertTrue(controller.is_started)

        controller.stop()
        self.assertFalse(sensor.connected)
        self.assertFalse(controller.is_started)


class Bmp3xxBarometricAdapterTests(unittest.TestCase):
    def test_translates_bmp3xx_readings_to_sample(self) -> None:
        device = FakeBmp3xx()
        adapter = Bmp3xxBarometricAdapter(device)  # type: ignore[arg-type]

        adapter.connect()
        sample = adapter.read_barometric()

        self.assertTrue(adapter.is_connected)
        self.assertEqual(
            sample,
            BarometricSample(
                pressure_pa=100_000.0,
                temperature_c=22.5,
            ),
        )

        adapter.disconnect()
        self.assertFalse(adapter.is_connected)


class AlternateBarometricControllerTests(unittest.TestCase):
    def test_stub_returns_deterministic_state(self) -> None:
        controller = BarometricControllerStub()

        controller.start()
        first = controller.read_state()
        second = controller.read_state()

        self.assertIs(first, second)
        self.assertTrue(controller.is_available)
        self.assertIsNone(controller.status_message)

    def test_unconfigured_controller_reports_and_raises_reason(self) -> None:
        controller = UnconfiguredBarometricController("sensor disabled")

        self.assertFalse(controller.is_available)
        self.assertFalse(controller.is_started)
        self.assertEqual(controller.status_message, "sensor disabled")
        self.assertIsNone(controller.latest_state)
        with self.assertRaisesRegex(RuntimeError, "sensor disabled"):
            controller.start()
        with self.assertRaisesRegex(RuntimeError, "sensor disabled"):
            controller.read_state()


class BarometricCliTests(unittest.TestCase):
    STATE = BarometricState(
        pressure_pa=101_325.0,
        temperature_c=20.0,
        altitude_m=100.0,
        relative_altitude_m=10.0,
        vertical_speed_mps=1.0,
        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    def test_formats_metric_state(self) -> None:
        output = format_state(self.STATE)

        self.assertIn("101325.0 Pa", output)
        self.assertIn("20.00 °C", output)
        self.assertIn("100.0 m", output)
        self.assertIn("1.00 m/s", output)

    def test_formats_imperial_state(self) -> None:
        output = format_state(self.STATE, imperial=True)

        self.assertIn("29.921 inHg", output)
        self.assertIn("68.00 °F", output)
        self.assertIn("328.1 ft", output)
        self.assertIn("196.9 ft/min", output)


if __name__ == "__main__":
    unittest.main()
