# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Normalize browser DeviceMotion payloads for navigation consumers."""

from __future__ import annotations

import math
from typing import Any

from controllers.navigation.navigation_sensor_if import MotionSample
from hardware_io.imu import Vector3

_DEG_TO_RAD = math.pi / 180.0


class BrowserMotionAdapter:
    """Translate browser DeviceMotion payloads into navigation motion samples."""

    @staticmethod
    def sample_from_payload(payload: Any) -> MotionSample:
        if not isinstance(payload, dict):
            raise ValueError("motion must be a JSON object")

        acceleration = payload.get("accelerationIncludingGravity")
        rotation = payload.get("rotationRate")
        if not isinstance(acceleration, dict):
            raise ValueError("accelerationIncludingGravity must be a JSON object")
        if not isinstance(rotation, dict):
            raise ValueError("rotationRate must be a JSON object")

        # DeviceMotion accelerationIncludingGravity is m/s². RotationRate is
        # degrees/second, while NavigationSensorIf requires radians/second.
        return MotionSample(
            acceleration_mps2=Vector3(
                _number(acceleration.get("x"), "acceleration.x"),
                _number(acceleration.get("y"), "acceleration.y"),
                _number(acceleration.get("z"), "acceleration.z"),
            ),
            angular_velocity_rad_s=Vector3(
                _number(rotation.get("beta"), "rotation.beta") * _DEG_TO_RAD,
                _number(rotation.get("gamma"), "rotation.gamma") * _DEG_TO_RAD,
                _number(rotation.get("alpha"), "rotation.alpha") * _DEG_TO_RAD,
            ),
        )


def _number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result
