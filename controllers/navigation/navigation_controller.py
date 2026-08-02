"""Coordinate vehicle motion, orientation, and optional GPS state."""

from __future__ import annotations

import math
import time
from collections.abc import Callable
from datetime import datetime
from threading import Lock

from hardware_io.imu import Vector3

from controllers.navigation.complementary_orientation_estimator import (
    ComplementaryOrientationEstimator,
)
from controllers.navigation.navigation_gps_source_if import (
    NavigationGpsSourceIf,
)
from controllers.navigation.motion_calibration import MotionCalibration
from controllers.navigation.navigation_sensor_if import (
    MotionSample,
    NavigationSensorIf,
)
from controllers.navigation.navigation_state import (
    GpsState,
    NavigationState,
)
from controllers.navigation.orientation_estimator_if import (
    OrientationEstimatorIf,
)


class NavigationController:
    """Coordinate normalized navigation inputs into current vehicle state."""

    STANDARD_GRAVITY_MPS2 = 9.80665

    def __init__(
        self,
        sensor: NavigationSensorIf,
        filter_time_constant_s: float = 0.5,
        orientation_estimator: OrientationEstimatorIf | None = None,
        gps_source: NavigationGpsSourceIf | None = None,
        monotonic_clock: Callable[[], float] = time.monotonic,
        wall_clock: Callable[[], datetime] = datetime.now,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        self._sensor = sensor
        self._gps_source = gps_source
        self._orientation_estimator = (
            orientation_estimator
            if orientation_estimator is not None
            else ComplementaryOrientationEstimator(
                filter_time_constant_s=filter_time_constant_s
            )
        )
        self._monotonic_clock = monotonic_clock
        self._wall_clock = wall_clock
        self._sleeper = sleeper
        self._started = False
        self._last_sample_time: float | None = None
        self._gps_lock = Lock()
        self._gps_state: GpsState | None = None
        self._calibration: MotionCalibration | None = None

    @property
    def is_started(self) -> bool:
        return self._started

    @property
    def calibration(self) -> MotionCalibration | None:
        """Return the active stationary calibration, if any."""

        return self._calibration

    def start(self) -> None:
        """Start all configured navigation sources."""

        if self._started:
            return

        self._sensor.connect()

        try:
            motion = self._correct_motion(self._sensor.read_motion())
            self._orientation_estimator.start(
                motion.acceleration_mps2
            )
            if self._gps_source is not None:
                self._gps_source.start(self.update_gps_state)
            sample_time = self._monotonic_clock()
        except Exception:
            if self._gps_source is not None:
                self._gps_source.stop()
            self._orientation_estimator.stop()
            self._sensor.disconnect()
            raise

        self._last_sample_time = sample_time
        self._started = True

    def stop(self) -> None:
        """Stop all configured navigation sources."""

        try:
            if self._gps_source is not None:
                self._gps_source.stop()
        finally:
            try:
                self._orientation_estimator.stop()
            finally:
                self._sensor.disconnect()

        self._started = False
        self._last_sample_time = None

    def reset_heading(self, heading_deg: float = 0.0) -> None:
        self._orientation_estimator.reset_heading(heading_deg)

    def calibrate_stationary(
        self,
        sample_count: int = 100,
        sample_interval_s: float = 0.01,
    ) -> MotionCalibration:
        """Measure sensor biases while the vehicle and sensor are stationary."""

        if not self._started:
            raise RuntimeError("navigation controller has not been started")
        if sample_count <= 0:
            raise ValueError("sample_count must be greater than zero")
        if sample_interval_s < 0.0:
            raise ValueError("sample_interval_s must not be negative")

        acceleration_sum = Vector3(0.0, 0.0, 0.0)
        angular_velocity_sum = Vector3(0.0, 0.0, 0.0)

        for index in range(sample_count):
            motion = self._sensor.read_motion()
            acceleration_sum = self._add_vectors(
                acceleration_sum, motion.acceleration_mps2
            )
            angular_velocity_sum = self._add_vectors(
                angular_velocity_sum, motion.angular_velocity_rad_s
            )
            if sample_interval_s > 0.0 and index + 1 < sample_count:
                self._sleeper(sample_interval_s)

        average_acceleration = self._divide_vector(
            acceleration_sum, sample_count
        )
        average_angular_velocity = self._divide_vector(
            angular_velocity_sum, sample_count
        )
        acceleration_magnitude = self._vector_magnitude(
            average_acceleration
        )
        if acceleration_magnitude <= 1e-9:
            raise RuntimeError(
                "stationary calibration measured no gravity vector"
            )

        expected_gravity = self._scale_vector(
            average_acceleration,
            self.STANDARD_GRAVITY_MPS2 / acceleration_magnitude,
        )
        calibration = MotionCalibration(
            acceleration_bias_mps2=self._subtract_vectors(
                average_acceleration, expected_gravity
            ),
            angular_velocity_bias_rad_s=average_angular_velocity,
            sample_count=sample_count,
        )
        self._calibration = calibration

        corrected_acceleration = self._subtract_vectors(
            average_acceleration, calibration.acceleration_bias_mps2
        )
        self._orientation_estimator.stop()
        self._orientation_estimator.start(corrected_acceleration)
        self._last_sample_time = self._monotonic_clock()
        return calibration

    def update_gps_state(self, gps_state: GpsState) -> None:
        """Accept the latest normalized GPS update.

        This method is safe to call from a GPS reader callback thread. It also
        permits application-managed GPS sources when ``gps_source`` is omitted.
        """

        with self._gps_lock:
            self._gps_state = gps_state

    def read_state(self) -> NavigationState:
        """Read motion and return current orientation and GPS state."""

        if not self._started or self._last_sample_time is None:
            raise RuntimeError("navigation controller has not been started")

        raw_motion = self._sensor.read_motion()
        motion = self._correct_motion(raw_motion)
        sample_time = self._monotonic_clock()
        elapsed_s = max(0.0, sample_time - self._last_sample_time)
        orientation = self._orientation_estimator.update(
            acceleration_mps2=motion.acceleration_mps2,
            angular_velocity_rad_s=motion.angular_velocity_rad_s,
            elapsed_s=elapsed_s,
        )
        self._last_sample_time = sample_time

        with self._gps_lock:
            gps_state = self._gps_state

        linear_acceleration = self._remove_gravity(
            acceleration=motion.acceleration_mps2,
            pitch_deg=orientation.pitch_deg,
            roll_deg=orientation.roll_deg,
        )

        return NavigationState(
            timestamp=self._wall_clock(),
            heading_deg=orientation.heading_deg,
            pitch_deg=orientation.pitch_deg,
            roll_deg=orientation.roll_deg,
            acceleration_mps2=raw_motion.acceleration_mps2,
            linear_acceleration_mps2=linear_acceleration,
            angular_velocity_rad_s=motion.angular_velocity_rad_s,
            gps=gps_state,
        )

    def _correct_motion(self, motion: MotionSample) -> MotionSample:
        calibration = self._calibration
        if calibration is None:
            return motion

        return MotionSample(
            acceleration_mps2=self._subtract_vectors(
                motion.acceleration_mps2,
                calibration.acceleration_bias_mps2,
            ),
            angular_velocity_rad_s=self._subtract_vectors(
                motion.angular_velocity_rad_s,
                calibration.angular_velocity_bias_rad_s,
            ),
        )

    @classmethod
    def _remove_gravity(
        cls,
        acceleration: Vector3,
        pitch_deg: float,
        roll_deg: float,
    ) -> Vector3:
        """Remove the estimated gravity vector from body-frame acceleration."""

        pitch_rad = math.radians(pitch_deg)
        roll_rad = math.radians(roll_deg)
        gravity = cls.STANDARD_GRAVITY_MPS2

        gravity_x = -gravity * math.sin(pitch_rad)
        gravity_y = (
            gravity * math.sin(roll_rad) * math.cos(pitch_rad)
        )
        gravity_z = (
            gravity * math.cos(roll_rad) * math.cos(pitch_rad)
        )

        return Vector3(
            x=acceleration.x - gravity_x,
            y=acceleration.y - gravity_y,
            z=acceleration.z - gravity_z,
        )

    @staticmethod
    def _add_vectors(left: Vector3, right: Vector3) -> Vector3:
        return Vector3(
            left.x + right.x,
            left.y + right.y,
            left.z + right.z,
        )

    @staticmethod
    def _subtract_vectors(left: Vector3, right: Vector3) -> Vector3:
        return Vector3(
            left.x - right.x,
            left.y - right.y,
            left.z - right.z,
        )

    @staticmethod
    def _divide_vector(vector: Vector3, divisor: int) -> Vector3:
        return Vector3(
            vector.x / divisor,
            vector.y / divisor,
            vector.z / divisor,
        )

    @staticmethod
    def _scale_vector(vector: Vector3, scale: float) -> Vector3:
        return Vector3(
            vector.x * scale,
            vector.y * scale,
            vector.z * scale,
        )

    @staticmethod
    def _vector_magnitude(vector: Vector3) -> float:
        return math.sqrt(vector.x**2 + vector.y**2 + vector.z**2)
