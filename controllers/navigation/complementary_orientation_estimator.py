"""Complementary-filter orientation estimation for a six-axis IMU."""

from __future__ import annotations

import math

from hardware_io.imu import Vector3

from controllers.navigation.orientation_estimator_if import (
    Orientation,
    OrientationEstimatorIf,
)


class ComplementaryOrientationEstimator(OrientationEstimatorIf):
    """Estimate relative orientation from acceleration and angular velocity."""

    def __init__(self, filter_time_constant_s: float = 0.5) -> None:
        if filter_time_constant_s < 0.0:
            raise ValueError("filter_time_constant_s must not be negative")

        self._filter_time_constant_s = filter_time_constant_s
        self._started = False
        self._heading_deg = 0.0
        self._pitch_deg = 0.0
        self._roll_deg = 0.0

    def start(self, acceleration_mps2: Vector3) -> None:
        self._pitch_deg, self._roll_deg = self._tilt_from_acceleration(
            acceleration_mps2
        )
        self._heading_deg = 0.0
        self._started = True

    def stop(self) -> None:
        self._started = False

    def update(
        self,
        acceleration_mps2: Vector3,
        angular_velocity_rad_s: Vector3,
        elapsed_s: float,
    ) -> Orientation:
        if not self._started:
            raise RuntimeError("orientation estimator has not been started")

        acceleration_pitch_deg, acceleration_roll_deg = (
            self._tilt_from_acceleration(acceleration_mps2)
        )
        gyro_roll_deg = self._roll_deg + math.degrees(
            angular_velocity_rad_s.x * elapsed_s
        )
        gyro_pitch_deg = self._pitch_deg + math.degrees(
            angular_velocity_rad_s.y * elapsed_s
        )
        filter_weight = self._filter_weight(elapsed_s)

        self._roll_deg = (
            filter_weight * gyro_roll_deg
            + (1.0 - filter_weight) * acceleration_roll_deg
        )
        self._pitch_deg = (
            filter_weight * gyro_pitch_deg
            + (1.0 - filter_weight) * acceleration_pitch_deg
        )
        self._heading_deg = (
            self._heading_deg
            + math.degrees(angular_velocity_rad_s.z * elapsed_s)
        ) % 360.0

        return Orientation(
            heading_deg=self._heading_deg,
            pitch_deg=self._pitch_deg,
            roll_deg=self._roll_deg,
        )

    def reset_heading(self, heading_deg: float = 0.0) -> None:
        if not math.isfinite(heading_deg):
            raise ValueError("heading_deg must be finite")

        self._heading_deg = heading_deg % 360.0

    def _filter_weight(self, elapsed_s: float) -> float:
        if elapsed_s <= 0.0:
            return 1.0

        return self._filter_time_constant_s / (
            self._filter_time_constant_s + elapsed_s
        )

    @staticmethod
    def _tilt_from_acceleration(
        acceleration: Vector3,
    ) -> tuple[float, float]:
        pitch_deg = math.degrees(
            math.atan2(
                -acceleration.x,
                math.hypot(acceleration.y, acceleration.z),
            )
        )
        roll_deg = math.degrees(
            math.atan2(acceleration.y, acceleration.z)
        )
        return pitch_deg, roll_deg
