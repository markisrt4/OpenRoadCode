"""Tests for navigation-state presentation through narrow UI contracts."""

from datetime import datetime
import math
import unittest
from unittest.mock import Mock

from controllers.navigation import (
    NavigationState,
    NavigationStatePresenter,
    PositionState,
)
from hardware_io.imu import Vector3
from ui.navigation import HeadingReference


class NavigationStatePresenterTest(unittest.TestCase):
    def test_presents_orientation_motion_position_and_ground_track(self) -> None:
        orientation = Mock()
        translation = Mock()
        position = Mock()
        ground_track = Mock()
        presenter = NavigationStatePresenter(
            orientation_ui=orientation,
            translation_ui=translation,
            position_ui=position,
            ground_track_ui=ground_track,
        )
        linear = Vector3(1.0, -2.0, 2.0)
        state = NavigationState(
            timestamp=datetime.now(),
            heading_deg=90.0,
            pitch_deg=10.0,
            roll_deg=-5.0,
            acceleration_mps2=Vector3(0.0, 0.0, 9.81),
            linear_acceleration_mps2=linear,
            angular_velocity_rad_s=Vector3(0.0, 0.0, 0.0),
            gps=PositionState(
                latitude_deg=42.0,
                longitude_deg=-83.0,
                altitude_m=200.0,
                speed_mps=4.0,
                course_deg=180.0,
                fix_mode=3,
                accuracy_m=3.0,
            ),
        )

        presenter.present(state)

        orientation.set_heading.assert_called_once_with(
            math.pi / 2,
            HeadingReference.RELATIVE,
        )
        orientation.set_pitch.assert_called_once_with(math.radians(10.0))
        orientation.set_roll.assert_called_once_with(math.radians(-5.0))
        translation.set_accel_x.assert_called_once_with(1.0)
        translation.set_accel_y.assert_called_once_with(-2.0)
        translation.set_accel_z.assert_called_once_with(2.0)
        translation.set_accel_total.assert_called_once_with(3.0)
        fix = position.set_position.call_args.args[0]
        self.assertAlmostEqual(fix.latitude_rad, math.radians(42.0))
        self.assertAlmostEqual(fix.longitude_rad, math.radians(-83.0))
        ground_track.set_ground_speed.assert_called_once_with(4.0)
        ground_track.set_course_over_ground.assert_called_once_with(math.pi)

    def test_no_fix_clears_position_and_ground_track(self) -> None:
        position = Mock()
        ground_track = Mock()
        presenter = NavigationStatePresenter(
            orientation_ui=Mock(),
            translation_ui=Mock(),
            position_ui=position,
            ground_track_ui=ground_track,
        )
        zero = Vector3(0.0, 0.0, 0.0)
        state = NavigationState(
            timestamp=datetime.now(),
            heading_deg=0.0,
            pitch_deg=0.0,
            roll_deg=0.0,
            acceleration_mps2=zero,
            linear_acceleration_mps2=zero,
            angular_velocity_rad_s=zero,
            gps=PositionState(),
        )

        presenter.present(state)

        position.set_position.assert_called_once_with(None)
        ground_track.set_ground_speed.assert_called_once_with(None)
        ground_track.set_course_over_ground.assert_called_once_with(None)
