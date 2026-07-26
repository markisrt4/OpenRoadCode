"""Shared Adafruit BMP3XX barometric pressure sensor implementation."""

from __future__ import annotations

import time
from typing import Any

from .barometric_sensor_if import BarometricSensorIf


class Bmp3xx(BarometricSensorIf):
    """Read pressure and sensor temperature from a BMP388 or BMP390 over I2C.

    Adafruit's BMP3XX driver detects and supports both sensor variants. The
    underlying driver reports pressure in hectopascals; this implementation
    converts it to pascals before exposing it through the hardware interface.
    """

    DEFAULT_ADDRESS = 0x77
    ALTERNATE_ADDRESS = 0x76

    _PASCALS_PER_HECTOPASCAL = 100.0
    # BMP3XX_I2C ends its constructor with a soft reset, but the upstream
    # driver returns before the reset has completed. An immediate forced-mode
    # read can therefore be ignored by the sensor, leaving the driver waiting
    # indefinitely for its data-ready bits.
    _RESET_SETTLE_TIME_S = 0.01

    def __init__(
        self,
        address: int = DEFAULT_ADDRESS,
        i2c: Any | None = None,
    ) -> None:
        """Create a BMP3XX sensor.

        Args:
            address: I2C address of the sensor.
            i2c: Optional pre-created CircuitPython-compatible I2C bus.
                When omitted, the Raspberry Pi's default I2C bus is used.
        """
        if not 0 <= address <= 0x7F:
            raise ValueError(
                f"I2C address must be between 0x00 and 0x7F: {address:#x}"
            )

        self._address = address
        self._provided_i2c = i2c

        self._i2c: Any | None = None
        self._sensor: Any | None = None
        self._owns_i2c = False

    @property
    def is_started(self) -> bool:
        """Return whether the sensor has been initialized."""
        return self._sensor is not None

    @property
    def address(self) -> int:
        """Return the configured I2C address."""
        return self._address

    def start(self) -> None:
        """Initialize the I2C bus and BMP3XX sensor."""
        if self.is_started:
            return

        try:
            import adafruit_bmp3xx
        except ImportError as exc:
            raise RuntimeError(
                "BMP3XX support requires the "
                "'adafruit-circuitpython-bmp3xx' package"
            ) from exc

        if self._provided_i2c is not None:
            self._i2c = self._provided_i2c
            self._owns_i2c = False
        else:
            try:
                import board
            except ImportError as exc:
                raise RuntimeError(
                    "BMP3XX support requires Adafruit Blinka on Linux"
                ) from exc

            self._i2c = board.I2C()
            self._owns_i2c = True

        try:
            sensor = adafruit_bmp3xx.BMP3XX_I2C(
                self._i2c,
                address=self._address,
            )
            time.sleep(self._RESET_SETTLE_TIME_S)
            self._sensor = sensor
        except Exception:
            self._release_i2c()
            raise

    def stop(self) -> None:
        """Release resources owned by the sensor."""
        self._sensor = None
        self._release_i2c()

    def get_pressure_pa(self) -> float:
        """Return atmospheric pressure in pascals."""
        sensor = self._require_sensor()
        pressure_hpa = float(sensor.pressure)
        return pressure_hpa * self._PASCALS_PER_HECTOPASCAL

    def get_temperature_c(self) -> float:
        """Return sensor temperature in degrees Celsius."""
        sensor = self._require_sensor()
        return float(sensor.temperature)

    def _require_sensor(self) -> Any:
        if self._sensor is None:
            raise RuntimeError(
                "BMP3XX has not been started; call start() first"
            )

        return self._sensor

    def _release_i2c(self) -> None:
        if (
            self._owns_i2c
            and self._i2c is not None
            and hasattr(self._i2c, "deinit")
        ):
            self._i2c.deinit()

        self._i2c = None
        self._owns_i2c = False

    def __enter__(self) -> Bmp3xx:
        self.start()
        return self

    def __exit__(
        self,
        _exception_type: object,
        _exception: object,
        _traceback: object,
    ) -> None:
        self.stop()
