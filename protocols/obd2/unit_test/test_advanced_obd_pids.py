# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

import pytest

from protocols.obd2.obd_pids import (
    AbsoluteEngineLoadPid,
    CommandedThrottleActuatorPid,
    FuelRailGaugePressurePid,
    FuelSystemStatusPid,
    IgnitionTimingAdvancePid,
    LongTermFuelTrimBank1Pid,
    OxygenSensor1EquivalenceRatioPid,
    ShortTermFuelTrimBank1Pid,
)


def test_fuel_system_status_decodes_both_status_bytes() -> None:
    assert FuelSystemStatusPid().decode(bytes([0x02, 0x00])) == (0x02, 0x00)


def test_short_term_fuel_trim_decode() -> None:
    assert ShortTermFuelTrimBank1Pid().decode(bytes([128])) == pytest.approx(0.0)
    assert ShortTermFuelTrimBank1Pid().decode(bytes([140])) == pytest.approx(9.375)


def test_long_term_fuel_trim_decode() -> None:
    assert LongTermFuelTrimBank1Pid().decode(bytes([128])) == pytest.approx(0.0)
    assert LongTermFuelTrimBank1Pid().decode(bytes([115])) == pytest.approx(-10.15625)


def test_ignition_timing_advance_decode() -> None:
    assert IgnitionTimingAdvancePid().decode(bytes([128])) == pytest.approx(0.0)
    assert IgnitionTimingAdvancePid().decode(bytes([148])) == pytest.approx(10.0)


def test_fuel_rail_pressure_decode() -> None:
    assert FuelRailGaugePressurePid().decode(bytes.fromhex("0138")) == pytest.approx(3120.0)


def test_measured_equivalence_ratio_decode() -> None:
    assert OxygenSensor1EquivalenceRatioPid().decode(bytes.fromhex("8000")) == pytest.approx(1.0)
    assert OxygenSensor1EquivalenceRatioPid().decode(bytes.fromhex("6666")) == pytest.approx(0.8, rel=1e-3)


def test_absolute_engine_load_decode() -> None:
    assert AbsoluteEngineLoadPid().decode(bytes.fromhex("00FF")) == pytest.approx(100.0)


def test_commanded_throttle_decode() -> None:
    assert CommandedThrottleActuatorPid().decode(bytes([128])) == pytest.approx(128.0 * 100.0 / 255.0)
