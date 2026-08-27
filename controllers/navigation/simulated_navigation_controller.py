# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Deterministic navigation simulation for development without hardware."""

from dataclasses import replace
from datetime import datetime
import math

from controllers.navigation.navigation_controller_stub import NavigationControllerStub
from controllers.navigation.navigation_state import (
    GroundMotionState,
    NavigationState,
    PositionState,
)
from hardware_io.imu import Vector3


class SimulatedNavigationController(NavigationControllerStub):
    """Generate changing attitude, motion, position, and ground motion."""

    def __init__(self, step_radians: float = 0.08) -> None:
        zero = Vector3(0.0, 0.0, 0.0)
        super().__init__(
            NavigationState(
                timestamp=datetime.now(),
                heading_deg=0.0,
                pitch_deg=0.0,
                roll_deg=0.0,
                acceleration_mps2=Vector3(0.0, 0.0, 9.80665),
                linear_acceleration_mps2=zero,
                angular_velocity_rad_s=zero,
                position=PositionState(
                    latitude_deg=42.3314,
                    longitude_deg=-83.0458,
                    altitude_m=180.0,
                    fix_mode=3,
                    satellites_visible=12,
                    satellites_used=9,
                    accuracy_m=3.0,
                    source="simulation",
                ),
                ground_motion=GroundMotionState(
                    speed_mps=0.0,
                    course_deg=0.0,
                    source="simulation",
                ),
            )
        )
        self._step_radians = step_radians
        self._phase = 0.0

    def read_state(self) -> NavigationState:
        current = super().read_state()
        self._phase += self._step_radians
        heading = (current.heading_deg + 1.5) % 360.0
        pitch = 12.0 * math.sin(self._phase * 0.7)
        roll = 18.0 * math.sin(self._phase)
        linear = Vector3(
            1.2 * math.sin(self._phase * 1.3),
            0.8 * math.cos(self._phase),
            0.15 * math.sin(self._phase * 0.5),
        )
        position = replace(
            current.position,
            latitude_deg=42.3314 + 0.002 * math.sin(self._phase * 0.1),
            longitude_deg=-83.0458 + 0.002 * math.cos(self._phase * 0.1),
            altitude_m=180.0 + 8.0 * math.sin(self._phase * 0.2),
        )
        ground_motion = replace(
            current.ground_motion,
            speed_mps=8.0 + 3.0 * math.sin(self._phase * 0.4),
            course_deg=heading,
        )
        state = replace(
            current,
            timestamp=datetime.now(),
            heading_deg=heading,
            pitch_deg=pitch,
            roll_deg=roll,
            acceleration_mps2=Vector3(linear.x, linear.y, 9.80665 + linear.z),
            linear_acceleration_mps2=linear,
            angular_velocity_rad_s=Vector3(0.01, 0.02, 0.04),
            position=position,
            ground_motion=ground_motion,
        )
        self.set_state(state)
        return state
