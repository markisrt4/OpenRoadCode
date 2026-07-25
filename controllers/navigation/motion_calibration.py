"""Motion-sensor calibration values."""

from dataclasses import dataclass

from hardware_io.imu import Vector3


@dataclass(frozen=True, slots=True)
class MotionCalibration:
    """Biases measured while the motion sensor is stationary."""

    acceleration_bias_mps2: Vector3
    angular_velocity_bias_rad_s: Vector3
    sample_count: int
