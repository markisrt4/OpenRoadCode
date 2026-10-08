# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

import math
import unittest

from controllers.navigation.complementary_orientation_estimator import (
    ComplementaryOrientationEstimator,
)
from hardware_io.imu import Vector3


class ComplementaryOrientationEstimatorTests(unittest.TestCase):
    def test_roll_wraps_across_positive_boundary(self) -> None:
        estimator = ComplementaryOrientationEstimator(filter_time_constant_s=1.0)
        estimator.start(Vector3(0.0, 0.0, 9.80665))

        orientation = estimator.update(
            acceleration_mps2=Vector3(0.0, 0.0, 9.80665),
            angular_velocity_rad_s=Vector3(math.radians(200.0), 0.0, 0.0),
            elapsed_s=1.0,
        )

        self.assertGreaterEqual(orientation.roll_deg, -180.0)
        self.assertLessEqual(orientation.roll_deg, 180.0)

    def test_roll_wraps_across_negative_boundary(self) -> None:
        estimator = ComplementaryOrientationEstimator(filter_time_constant_s=1.0)
        estimator.start(Vector3(0.0, 0.0, 9.80665))

        orientation = estimator.update(
            acceleration_mps2=Vector3(0.0, 0.0, 9.80665),
            angular_velocity_rad_s=Vector3(math.radians(-200.0), 0.0, 0.0),
            elapsed_s=1.0,
        )

        self.assertGreaterEqual(orientation.roll_deg, -180.0)
        self.assertLessEqual(orientation.roll_deg, 180.0)

    def test_roll_blends_across_wrap_using_shortest_path(self) -> None:
        estimator = ComplementaryOrientationEstimator(filter_time_constant_s=1.0)
        near_positive_180 = Vector3(0.0, math.sin(math.radians(179.0)), math.cos(math.radians(179.0)))
        estimator.start(near_positive_180)

        near_negative_180 = Vector3(0.0, math.sin(math.radians(-179.0)), math.cos(math.radians(-179.0)))
        orientation = estimator.update(
            acceleration_mps2=near_negative_180,
            angular_velocity_rad_s=Vector3(0.0, 0.0, 0.0),
            elapsed_s=1.0,
        )

        self.assertGreater(abs(orientation.roll_deg), 170.0)

    def test_repeated_roll_integration_stays_in_valid_domain(self) -> None:
        estimator = ComplementaryOrientationEstimator(filter_time_constant_s=10.0)
        estimator.start(Vector3(0.0, 0.0, 9.80665))

        for _ in range(100):
            orientation = estimator.update(
                acceleration_mps2=Vector3(0.0, 0.0, 9.80665),
                angular_velocity_rad_s=Vector3(math.radians(90.0), 0.0, 0.0),
                elapsed_s=0.1,
            )
            self.assertGreaterEqual(orientation.roll_deg, -180.0)
            self.assertLessEqual(orientation.roll_deg, 180.0)


if __name__ == "__main__":
    unittest.main()
