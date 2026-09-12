# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from datetime import datetime

import pytest

from controllers.automotive import EngineInductionType, VehicleConfiguration
from controllers.automotive.engine_analysis import (
    EngineOperatingMode,
    FuelControlMode,
)
from controllers.automotive.engine_analyzer import EngineAnalyzer
from controllers.automotive.vehicle_state import VehicleState


def _state(**overrides) -> VehicleState:
    values = dict(
        timestamp=datetime(2026, 9, 12, 12, 0, 0),
        engine_speed_rad_s=200.0,
        vehicle_speed_m_s=20.0,
        accelerator_pedal_position=0.12,
        throttle_position=0.20,
        commanded_throttle_position=0.18,
        engine_load=0.40,
        absolute_engine_load=0.45,
        coolant_temperature_k=360.0,
        commanded_equivalence_ratio=1.0,
        measured_equivalence_ratio=1.01,
        short_term_fuel_trim_bank1=0.02,
        long_term_fuel_trim_bank1=-0.01,
        fuel_system_status_1=0x02,
        boost_pressure_pa=0.0,
    )
    values.update(overrides)
    return VehicleState(**values)


def test_cruise_analysis_combines_reported_ecu_facts() -> None:
    analysis = EngineAnalyzer(
        VehicleConfiguration(induction=EngineInductionType.TURBOCHARGED)
    ).analyze(_state())

    assert analysis.operating_mode is EngineOperatingMode.CRUISE
    assert analysis.fuel_control_mode is FuelControlMode.CLOSED_LOOP
    assert analysis.engine_running is True
    assert analysis.warmed_up is True
    assert analysis.high_load is False
    assert analysis.enrichment_active is False
    assert analysis.forced_induction_active is False
    assert analysis.fuel_trim_total == pytest.approx(0.01)
    assert analysis.mixture_tracking_error == pytest.approx(0.01)
    assert analysis.throttle_tracking_error == pytest.approx(0.02)


def test_high_load_and_enrichment_are_derived() -> None:
    analysis = EngineAnalyzer(
        VehicleConfiguration(induction=EngineInductionType.TURBOCHARGED)
    ).analyze(
        _state(
            accelerator_pedal_position=0.65,
            throttle_position=0.70,
            absolute_engine_load=0.90,
            commanded_equivalence_ratio=0.82,
            measured_equivalence_ratio=0.84,
            boost_pressure_pa=55_000.0,
        )
    )

    assert analysis.operating_mode is EngineOperatingMode.HIGH_LOAD
    assert analysis.high_load is True
    assert analysis.enrichment_active is True
    assert analysis.forced_induction_active is True
    assert analysis.mixture_tracking_error == pytest.approx(0.02)


def test_naturally_aspirated_configuration_never_reports_forced_induction() -> None:
    analysis = EngineAnalyzer(
        VehicleConfiguration(
            induction=EngineInductionType.NATURALLY_ASPIRATED
        )
    ).analyze(_state(boost_pressure_pa=80_000.0))

    assert analysis.forced_induction_active is False


def test_idle_and_engine_off_are_distinct() -> None:
    analyzer = EngineAnalyzer(VehicleConfiguration())

    idle = analyzer.analyze(
        _state(
            vehicle_speed_m_s=0.0,
            accelerator_pedal_position=0.01,
            engine_speed_rad_s=90.0,
        )
    )
    off = analyzer.analyze(_state(engine_speed_rad_s=0.0))

    assert idle.operating_mode is EngineOperatingMode.IDLE
    assert off.operating_mode is EngineOperatingMode.OFF


def test_missing_telemetry_remains_unknown_instead_of_invented() -> None:
    analysis = EngineAnalyzer(
        VehicleConfiguration(induction=EngineInductionType.TURBOCHARGED)
    ).analyze(
        VehicleState(
            timestamp=datetime(2026, 9, 12, 12, 0, 0),
        )
    )

    assert analysis.operating_mode is EngineOperatingMode.UNKNOWN
    assert analysis.fuel_control_mode is FuelControlMode.UNKNOWN
    assert analysis.engine_running is None
    assert analysis.warmed_up is None
    assert analysis.high_load is None
    assert analysis.enrichment_active is None
    assert analysis.forced_induction_active is None
    assert analysis.fuel_trim_total is None
    assert analysis.mixture_tracking_error is None
    assert analysis.throttle_tracking_error is None


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (0x01, FuelControlMode.OPEN_LOOP_WARMUP),
        (0x02, FuelControlMode.CLOSED_LOOP),
        (0x04, FuelControlMode.OPEN_LOOP_LOAD_OR_DECEL),
        (0x08, FuelControlMode.OPEN_LOOP_FAULT),
        (0x10, FuelControlMode.CLOSED_LOOP_FAULT),
        (0x40, FuelControlMode.UNKNOWN),
    ],
)
def test_fuel_system_status_decoding(status, expected) -> None:
    analysis = EngineAnalyzer(VehicleConfiguration()).analyze(
        _state(fuel_system_status_1=status)
    )
    assert analysis.fuel_control_mode is expected
