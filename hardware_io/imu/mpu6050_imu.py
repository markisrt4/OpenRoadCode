"""Adafruit MPU-6050 inertial measurement unit implementation."""

from __future__ import annotations

from typing import Any

from hardware_io.imu.imu_if import ImuIf
from hardware_io.imu.imu_types import Vector3


class Mpu6050Imu(ImuIf):
    """Provide accelerometer and gyroscope data from an MPU-6050."""

    DEFAULT_ADDRESS = 0x68

    def __init__(
        self,
        i2c_bus: Any | None = None,
        address: int = DEFAULT_ADDRESS,
    ) -> None:
        """Initialize the MPU-6050 driver configuration.

        Args:
            i2c_bus:
                Optional existing CircuitPython-compatible I2C bus. When
                omitted, the driver creates the default board I2C bus.

            address:
                I2C address of the MPU-6050. The default address is 0x68.
        """
        self._i2c_bus = i2c_bus
        self._address = address

        self._owns_i2c_bus = i2c_bus is None
        self._sensor: Any | None = None

    def start(self) -> None:
        """Initialize the I2C bus and MPU-6050 sensor."""

        if self._sensor is not None:
            return

        try:
            import adafruit_mpu6050
        except ImportError as exc:
            raise RuntimeError(
                "MPU-6050 support requires the "
                "'adafruit-circuitpython-mpu6050' package "
                f"({exc})."
            ) from exc

        if self._i2c_bus is None:
            try:
                import board
            except ImportError as exc:
                raise RuntimeError(
                    "Unable to load the Adafruit Blinka board support "
                    f"for this system ({exc})."
                ) from exc

        try:
            if self._i2c_bus is None:
                self._i2c_bus = board.I2C()

            self._sensor = adafruit_mpu6050.MPU6050(
                self._i2c_bus,
                address=self._address,
            )
        except Exception as exc:
            self._sensor = None

            if self._owns_i2c_bus:
                self._release_i2c_bus()

            raise RuntimeError(
                f"Unable to initialize MPU-6050 at address "
                f"0x{self._address:02X}: {exc}"
            ) from exc

    def stop(self) -> None:
        """Release resources owned by the MPU-6050 driver."""

        self._sensor = None

        if self._owns_i2c_bus:
            self._release_i2c_bus()

    def is_connected(self) -> bool:
        """Return whether the MPU-6050 has been initialized."""

        return self._sensor is not None

    def get_acceleration_mps2(self) -> Vector3:
        """Return acceleration along each axis in meters per second squared."""

        sensor = self._require_sensor()
        acceleration = sensor.acceleration

        return Vector3(
            x=float(acceleration[0]),
            y=float(acceleration[1]),
            z=float(acceleration[2]),
        )

    def get_angular_velocity_rad_s(self) -> Vector3:
        """Return angular velocity along each axis in radians per second."""

        sensor = self._require_sensor()
        angular_velocity = sensor.gyro

        return Vector3(
            x=float(angular_velocity[0]),
            y=float(angular_velocity[1]),
            z=float(angular_velocity[2]),
        )

    def _require_sensor(self) -> Any:
        """Return the initialized sensor or raise an error."""

        if self._sensor is None:
            raise RuntimeError("MPU-6050 has not been started")

        return self._sensor

    def _release_i2c_bus(self) -> None:
        """Release the internally created I2C bus."""

        if self._i2c_bus is None:
            return

        deinit = getattr(self._i2c_bus, "deinit", None)

        if callable(deinit):
            deinit()

        self._i2c_bus = None
