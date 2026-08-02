from __future__ import annotations


class _Mode01Pid:
    mode = 0x01
    unit = ""


class EngineLoadPid(_Mode01Pid):
    """Decode calculated engine load as a percentage."""
    pid = 0x04
    unit = "%"

    def decode(self, data: bytes) -> float | None:
        return None if len(data) < 1 else data[0] * 100.0 / 255.0


class EngineRpmPid(_Mode01Pid):
    """Decode engine speed in revolutions per minute."""
    pid = 0x0C
    unit = "rpm"

    def decode(self, data: bytes) -> float | None:
        return None if len(data) < 2 else ((data[0] << 8) | data[1]) / 4.0


class VehicleSpeedPid(_Mode01Pid):
    """Decode vehicle speed in kilometers per hour."""
    pid = 0x0D
    unit = "km/h"

    def decode(self, data: bytes) -> int | None:
        return None if len(data) < 1 else data[0]


class IntakeManifoldPressurePid(_Mode01Pid):
    """Decode absolute intake-manifold pressure in kilopascals."""
    pid = 0x0B
    unit = "kPa"

    def decode(self, data: bytes) -> int | None:
        return None if len(data) < 1 else data[0]


class BarometricPressurePid(_Mode01Pid):
    """Decode barometric pressure in kilopascals."""
    pid = 0x33
    unit = "kPa"

    def decode(self, data: bytes) -> int | None:
        return None if len(data) < 1 else data[0]


class ThrottlePositionPid(_Mode01Pid):
    """Decode absolute throttle position as a percentage."""
    pid = 0x11
    unit = "%"

    def decode(self, data: bytes) -> float | None:
        return None if len(data) < 1 else data[0] * 100.0 / 255.0


class AcceleratorPedalPositionPid(_Mode01Pid):
    """Relative accelerator pedal position D, mode 01 PID 49."""

    pid = 0x49
    unit = "%"

    def decode(self, data: bytes) -> float | None:
        return None if len(data) < 1 else data[0] * 100.0 / 255.0


class CoolantTempPid(_Mode01Pid):
    """Decode engine coolant temperature in degrees Celsius."""
    pid = 0x05
    unit = "°C"

    def decode(self, data: bytes) -> int | None:
        return None if len(data) < 1 else data[0] - 40


class IntakeAirTempPid(_Mode01Pid):
    """Decode intake-air temperature in degrees Celsius."""
    pid = 0x0F
    unit = "°C"

    def decode(self, data: bytes) -> int | None:
        return None if len(data) < 1 else data[0] - 40


class MassAirFlowPid(_Mode01Pid):
    """Decode mass-air flow in grams per second."""
    pid = 0x10
    unit = "g/s"

    def decode(self, data: bytes) -> float | None:
        return None if len(data) < 2 else ((data[0] << 8) | data[1]) / 100.0


class FuelLevelPid(_Mode01Pid):
    """Decode fuel-tank level input as a percentage."""
    pid = 0x2F
    unit = "%"

    def decode(self, data: bytes) -> float | None:
        return None if len(data) < 1 else data[0] * 100.0 / 255.0


class ControlModuleVoltagePid(_Mode01Pid):
    """Decode control-module supply voltage in volts."""
    pid = 0x42
    unit = "V"

    def decode(self, data: bytes) -> float | None:
        return None if len(data) < 2 else ((data[0] << 8) | data[1]) / 1000.0
