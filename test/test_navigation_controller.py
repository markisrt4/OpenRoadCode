import math
import unittest
from collections.abc import Callable
from datetime import datetime

from controllers.navigation import (
    GpsdNavigationAdapter,
    GpsState,
    MotionSample,
    Mpu6050NavigationAdapter,
    NavigationController,
    Orientation,
)
from hardware_io.gps import GpsData
from hardware_io.imu import Vector3


class FakeNavigationSensor:
    def __init__(
        self,
        acceleration: Vector3 = Vector3(0.0, 0.0, 9.80665),
        angular_velocity: Vector3 = Vector3(0.0, 0.0, 0.0),
    ) -> None:
        self.acceleration = acceleration
        self.angular_velocity = angular_velocity
        self.started = False

    def connect(self) -> None:
        self.started = True

    def disconnect(self) -> None:
        self.started = False

    @property
    def is_connected(self) -> bool:
        return self.started

    def read_motion(self) -> MotionSample:
        if not self.started:
            raise RuntimeError("fake sensor has not been started")
        return MotionSample(self.acceleration, self.angular_velocity)


class FakeGpsSource:
    def __init__(self, state: GpsState) -> None:
        self.state = state
        self.started = False

    def start(self, callback: Callable[[GpsState], None]) -> None:
        self.started = True
        callback(self.state)

    def stop(self) -> None:
        self.started = False


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


class FixedOrientationEstimator:
    def __init__(self) -> None:
        self.started = False
        self.heading_deg = 123.0

    def start(self, acceleration_mps2: Vector3) -> None:
        self.started = True

    def stop(self) -> None:
        self.started = False

    def update(
        self,
        acceleration_mps2: Vector3,
        angular_velocity_rad_s: Vector3,
        elapsed_s: float,
    ) -> Orientation:
        return Orientation(self.heading_deg, 4.0, 5.0)

    def reset_heading(self, heading_deg: float = 0.0) -> None:
        self.heading_deg = heading_deg


class NavigationControllerTests(unittest.TestCase):
    def test_level_stationary_imu_reports_zero_orientation(self) -> None:
        imu = FakeNavigationSensor()
        clock = FakeClock()
        timestamp = datetime(2026, 1, 2, 3, 4, 5)
        controller = NavigationController(
            imu, monotonic_clock=clock, wall_clock=lambda: timestamp
        )

        controller.start()
        clock.now = 0.1
        state = controller.read_state()

        self.assertEqual(state.timestamp, timestamp)
        self.assertAlmostEqual(state.heading_deg, 0.0)
        self.assertAlmostEqual(state.pitch_deg, 0.0)
        self.assertAlmostEqual(state.roll_deg, 0.0)
        self.assertEqual(state.acceleration_mps2, imu.acceleration)
        self.assertAlmostEqual(state.linear_acceleration_mps2.x, 0.0)
        self.assertAlmostEqual(state.linear_acceleration_mps2.y, 0.0)
        self.assertAlmostEqual(state.linear_acceleration_mps2.z, 0.0)

    def test_integrates_relative_heading_from_z_gyro(self) -> None:
        imu = FakeNavigationSensor(
            angular_velocity=Vector3(0.0, 0.0, math.pi / 2.0)
        )
        clock = FakeClock()
        controller = NavigationController(imu, monotonic_clock=clock)

        controller.start()
        clock.now = 1.0
        state = controller.read_state()

        self.assertAlmostEqual(state.heading_deg, 90.0)

    def test_initializes_pitch_and_roll_from_acceleration(self) -> None:
        imu = FakeNavigationSensor(
            acceleration=Vector3(
                -9.80665 / math.sqrt(2.0),
                0.0,
                9.80665 / math.sqrt(2.0),
            )
        )
        clock = FakeClock()
        controller = NavigationController(imu, monotonic_clock=clock)

        controller.start()
        state = controller.read_state()

        self.assertAlmostEqual(state.pitch_deg, 45.0)
        self.assertAlmostEqual(state.roll_deg, 0.0)
        self.assertAlmostEqual(state.linear_acceleration_mps2.x, 0.0)
        self.assertAlmostEqual(state.linear_acceleration_mps2.z, 0.0)

    def test_reset_heading_normalizes_degrees(self) -> None:
        controller = NavigationController(FakeNavigationSensor())

        controller.start()
        controller.reset_heading(370.0)
        state = controller.read_state()

        self.assertAlmostEqual(state.heading_deg, 10.0)

    def test_requires_start_before_reading(self) -> None:
        controller = NavigationController(FakeNavigationSensor())

        with self.assertRaises(RuntimeError):
            controller.read_state()

    def test_stop_releases_imu(self) -> None:
        imu = FakeNavigationSensor()
        controller = NavigationController(imu)

        controller.start()
        controller.stop()

        self.assertFalse(controller.is_started)
        self.assertFalse(imu.started)

    def test_rejects_negative_filter_time_constant(self) -> None:
        with self.assertRaises(ValueError):
            NavigationController(
                FakeNavigationSensor(), filter_time_constant_s=-0.1
            )

    def test_stationary_calibration_removes_sensor_biases(self) -> None:
        sensor = FakeNavigationSensor(
            acceleration=Vector3(0.0, 0.0, 10.0),
            angular_velocity=Vector3(0.0, 0.0, 0.1),
        )
        clock = FakeClock()
        controller = NavigationController(
            sensor,
            monotonic_clock=clock,
            sleeper=lambda _seconds: None,
        )

        controller.start()
        calibration = controller.calibrate_stationary(
            sample_count=10,
            sample_interval_s=0.0,
        )
        clock.now = 1.0
        state = controller.read_state()

        self.assertEqual(calibration.sample_count, 10)
        self.assertAlmostEqual(
            calibration.acceleration_bias_mps2.z,
            10.0 - controller.STANDARD_GRAVITY_MPS2,
        )
        self.assertAlmostEqual(
            calibration.angular_velocity_bias_rad_s.z, 0.1
        )
        self.assertAlmostEqual(state.heading_deg, 0.0)
        self.assertAlmostEqual(state.linear_acceleration_mps2.z, 0.0)
        self.assertEqual(state.acceleration_mps2.z, 10.0)

    def test_calibration_requires_started_controller(self) -> None:
        controller = NavigationController(FakeNavigationSensor())

        with self.assertRaises(RuntimeError):
            controller.calibrate_stationary()

    def test_uses_injected_orientation_estimator(self) -> None:
        estimator = FixedOrientationEstimator()
        controller = NavigationController(
            FakeNavigationSensor(),
            orientation_estimator=estimator,  # type: ignore[arg-type]
        )

        controller.start()
        state = controller.read_state()

        self.assertTrue(estimator.started)
        self.assertEqual(state.heading_deg, 123.0)
        self.assertEqual(state.pitch_deg, 4.0)
        self.assertEqual(state.roll_deg, 5.0)

    def test_includes_optional_gps_state(self) -> None:
        gps_state = GpsState(
            latitude_deg=42.5,
            longitude_deg=-83.0,
            speed_mps=12.0,
            course_deg=180.0,
            fix_mode=3,
        )
        gps_source = FakeGpsSource(gps_state)
        controller = NavigationController(
            FakeNavigationSensor(),
            gps_source=gps_source,  # type: ignore[arg-type]
        )

        controller.start()
        state = controller.read_state()
        controller.stop()

        self.assertEqual(state.gps, gps_state)
        self.assertTrue(gps_state.has_fix)
        self.assertFalse(gps_source.started)

    def test_gps_state_can_be_updated_without_managed_source(self) -> None:
        controller = NavigationController(FakeNavigationSensor())
        gps_state = GpsState(fix_mode=2, latitude_deg=42.0)

        controller.update_gps_state(gps_state)
        controller.start()
        state = controller.read_state()

        self.assertEqual(state.gps, gps_state)


class Mpu6050NavigationAdapterTests(unittest.TestCase):
    def test_translates_imu_readings_to_motion_sample(self) -> None:
        class FakeMpu6050:
            def __init__(self) -> None:
                self.started = False

            def start(self) -> None:
                self.started = True

            def stop(self) -> None:
                self.started = False

            def is_connected(self) -> bool:
                return self.started

            def get_acceleration_mps2(self) -> Vector3:
                return Vector3(1.0, 2.0, 3.0)

            def get_angular_velocity_rad_s(self) -> Vector3:
                return Vector3(4.0, 5.0, 6.0)

        device = FakeMpu6050()
        adapter = Mpu6050NavigationAdapter(
            device  # type: ignore[arg-type]
        )

        adapter.connect()
        sample = adapter.read_motion()
        adapter.disconnect()

        self.assertEqual(
            sample.acceleration_mps2, Vector3(1.0, 2.0, 3.0)
        )
        self.assertEqual(
            sample.angular_velocity_rad_s, Vector3(4.0, 5.0, 6.0)
        )
        self.assertFalse(adapter.is_connected)


class GpsdNavigationAdapterTests(unittest.TestCase):
    def test_translates_gpsd_report_to_gps_state(self) -> None:
        class FakeGpsReader:
            def __init__(self) -> None:
                self.callback: Callable[[GpsData], None] | None = None
                self.stopped = False

            def start(
                self,
                callback: Callable[[GpsData], None] | None = None,
            ) -> None:
                self.callback = callback

            def stop(self) -> None:
                self.stopped = True

        reader = FakeGpsReader()
        adapter = GpsdNavigationAdapter(
            reader  # type: ignore[arg-type]
        )
        received: list[GpsState] = []

        adapter.start(received.append)
        assert reader.callback is not None
        reader.callback(
            GpsData(
                latitude=42.5,
                longitude=-83.0,
                altitude=200.0,
                speed=15.0,
                track=180.0,
                mode=3,
                satellites_visible=10,
                satellites_used=8,
            )
        )
        adapter.stop()

        self.assertEqual(len(received), 1)
        self.assertEqual(received[0].latitude_deg, 42.5)
        self.assertEqual(received[0].course_deg, 180.0)
        self.assertTrue(received[0].has_fix)
        self.assertTrue(reader.stopped)


if __name__ == "__main__":
    unittest.main()
