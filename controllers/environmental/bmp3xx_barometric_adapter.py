"""BMP3XX adapter for the environmental controller."""

from __future__ import annotations

from hardware_io.environmental import Bmp3xx

from .barometric_source_if import (
    BarometricSample,
    BarometricSourceIf,
)


class Bmp3xxBarometricAdapter(BarometricSourceIf):
    """Translate BMP388/BMP390 hardware readings into controller samples."""

    def __init__(self, device: Bmp3xx | None = None) -> None:
        self._device = device or Bmp3xx()

    @property
    def is_connected(self) -> bool:
        return self._device.is_started

    def connect(self) -> None:
        self._device.start()

    def disconnect(self) -> None:
        self._device.stop()

    def read_barometric(self) -> BarometricSample:
        return BarometricSample(
            pressure_pa=self._device.get_pressure_pa(),
            temperature_c=self._device.get_temperature_c(),
        )
