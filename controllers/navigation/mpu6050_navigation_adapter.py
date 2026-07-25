"""MPU-6050 adapter for the navigation controller."""

from hardware_io.imu import Mpu6050Imu

from controllers.navigation.navigation_sensor_if import (
    MotionSample,
    NavigationSensorIf,
)


class Mpu6050NavigationAdapter(NavigationSensorIf):
    """Translate MPU-6050 readings into normalized navigation samples."""

    def __init__(self, device: Mpu6050Imu | None = None) -> None:
        self._device = device or Mpu6050Imu()

    @property
    def is_connected(self) -> bool:
        return self._device.is_connected()

    def connect(self) -> None:
        self._device.start()

    def disconnect(self) -> None:
        self._device.stop()

    def read_motion(self) -> MotionSample:
        return MotionSample(
            acceleration_mps2=self._device.get_acceleration_mps2(),
            angular_velocity_rad_s=(
                self._device.get_angular_velocity_rad_s()
            ),
        )
