# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations


class _Mode01Pid:
    mode = 0x01
    unit = ""


class FuelSystemStatusPid(_Mode01Pid):
    """Decode raw fuel-system status bytes for bank/system 1 and 2."""
    pid = 0x03
    unit = "encoded"

    def decode(self, data: bytes) -> tuple[int, int | None] | None:
        if len(data) < 1:
            return None
        second = data[1] if len(data) >= 2 else None
        return data[0], second


class ShortTermFuelTrimBank1Pid(_Mode01Pid):
    """Decode short-term fuel trim for bank 1 as a percentage."""
    pid = 0x06
    unit = "%"

    def decode(self, data: bytes) -> float | None:
        return None if len(data) < 1 else data[0] / 1.28 - 100.0


class LongTermFuelTrimBank1Pid(_Mode01Pid):
    """Decode long-term fuel trim for bank 1 as a percentage."""
    pid = 0x07
    unit = "%"

    def decode(self, data: bytes) -> float | None:
        return None if len(data) < 1 else data[0] / 1.28 - 100.0


class IgnitionTimingAdvancePid(_Mode01Pid):
    """Decode ignition timing advance in crankshaft degrees."""
    pid = 0x0E
    unit = "deg"

    def decode(self, data: bytes) -> float | None:
        return None if len(data) < 1 else data[0] / 2.0 - 64.0


class FuelRailGaugePressurePid(_Mode01Pid):
    """Decode fuel-rail gauge pressure in kilopascals."""
    pid = 0x23
    unit = "kPa"

    def decode(self, data: bytes) -> float | None:
        return None if len(data) < 2 else ((data[0] << 8) | data[1]) * 10.0


class OxygenSensor1EquivalenceRatioPid(_Mode01Pid):
    """Decode wideband oxygen sensor 1 air/fuel equivalence ratio."""
    pid = 0x34
    unit = "ratio"

    def decode(self, data: bytes) -> float | None:
        return None if len(data) < 2 else ((data[0] << 8) | data[1]) / 32768.0


class AbsoluteEngineLoadPid(_Mode01Pid):
    """Decode absolute engine load as a percentage."""
    pid = 0x43
    unit = "%"

    def decode(self, data: bytes) -> float | None:
        return None if len(data) < 2 else ((data[0] << 8) | data[1]) / 2.55


class CommandedThrottleActuatorPid(_Mode01Pid):
    """Decode commanded throttle actuator position as a percentage."""
    pid = 0x4C
    unit = "%"

    def decode(self, data: bytes) -> float | None:
        return None if len(data) < 1 else data[0] * 100.0 / 255.0


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


class CommandedEquivalenceRatioPid(_Mode01Pid):
    """Decode commanded equivalence ratio (lambda-like ratio, 1.0 = stoich)."""
    pid = 0x44
    unit = "ratio"

    def decode(self, data: bytes) -> float | None:
        return None if len(data) < 2 else ((data[0] << 8) | data[1]) / 32768.0


class EngineFuelRatePid(_Mode01Pid):
    """Decode engine fuel rate in liters per hour."""
    pid = 0x5E
    unit = "L/h"

    def decode(self, data: bytes) -> float | None:
        return None if len(data) < 2 else ((data[0] << 8) | data[1]) / 20.0


class ControlModuleVoltagePid(_Mode01Pid):
    """Decode control-module supply voltage in volts."""
    pid = 0x42
    unit = "V"

    def decode(self, data: bytes) -> float | None:
        return None if len(data) < 2 else ((data[0] << 8) | data[1]) / 1000.0
