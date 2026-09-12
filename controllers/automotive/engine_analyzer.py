# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

from controllers.automotive.engine_analysis import (
    EngineAnalysis,
    EngineOperatingMode,
    FuelControlMode,
)
from controllers.automotive.vehicle_configuration import VehicleConfiguration
from controllers.automotive.vehicle_state import VehicleState


class EngineAnalyzer:
    """Interpret normalized engine telemetry without changing source facts."""

    _RUNNING_THRESHOLD_RAD_S = 20.0
    _IDLE_SPEED_M_S = 1.0
    _IDLE_PEDAL_MAX = 0.05
    _CRUISE_SPEED_M_S = 6.7
    _CRUISE_PEDAL_MAX = 0.35
    _HIGH_LOAD_THRESHOLD = 0.75
    _ACCELERATOR_THRESHOLD = 0.25
    _THROTTLE_THRESHOLD = 0.35
    _WARM_COOLANT_K = 344.15  # 160 F
    _ENRICHMENT_LAMBDA = 0.97
    _BOOST_THRESHOLD_PA = 6_894.757  # ~1 psi

    def __init__(self, configuration: VehicleConfiguration) -> None:
        self._configuration = configuration

    def analyze(self, state: VehicleState) -> EngineAnalysis:
        engine_running = self._engine_running(state)
        warmed_up = self._warmed_up(state)
        high_load = self._high_load(state)
        enrichment = self._enrichment_active(state)
        forced_induction = self._forced_induction_active(state)

        return EngineAnalysis(
            operating_mode=self._operating_mode(
                state,
                engine_running=engine_running,
                high_load=high_load,
            ),
            fuel_control_mode=self._fuel_control_mode(state.fuel_system_status_1),
            engine_running=engine_running,
            warmed_up=warmed_up,
            enrichment_active=enrichment,
            high_load=high_load,
            forced_induction_active=forced_induction,
            fuel_trim_total=self._sum_optional(
                state.short_term_fuel_trim_bank1,
                state.long_term_fuel_trim_bank1,
            ),
            mixture_tracking_error=self._difference_optional(
                state.measured_equivalence_ratio,
                state.commanded_equivalence_ratio,
            ),
            throttle_tracking_error=self._difference_optional(
                state.throttle_position,
                state.commanded_throttle_position,
            ),
        )

    @classmethod
    def _engine_running(cls, state: VehicleState) -> bool | None:
        if state.engine_speed_rad_s is None:
            return None
        return state.engine_speed_rad_s >= cls._RUNNING_THRESHOLD_RAD_S

    @classmethod
    def _warmed_up(cls, state: VehicleState) -> bool | None:
        if state.coolant_temperature_k is None:
            return None
        return state.coolant_temperature_k >= cls._WARM_COOLANT_K

    @classmethod
    def _high_load(cls, state: VehicleState) -> bool | None:
        load = (
            state.absolute_engine_load
            if state.absolute_engine_load is not None
            else state.engine_load
        )
        if load is None:
            return None
        return load >= cls._HIGH_LOAD_THRESHOLD

    @classmethod
    def _enrichment_active(cls, state: VehicleState) -> bool | None:
        if state.commanded_equivalence_ratio is None:
            return None
        return state.commanded_equivalence_ratio < cls._ENRICHMENT_LAMBDA

    def _forced_induction_active(self, state: VehicleState) -> bool | None:
        if not self._configuration.induction.is_forced_induction:
            return False
        if state.boost_pressure_pa is None:
            return None
        return state.boost_pressure_pa > self._BOOST_THRESHOLD_PA

    @classmethod
    def _operating_mode(
        cls,
        state: VehicleState,
        *,
        engine_running: bool | None,
        high_load: bool | None,
    ) -> EngineOperatingMode:
        if engine_running is False:
            return EngineOperatingMode.OFF
        if engine_running is None:
            return EngineOperatingMode.UNKNOWN

        speed = state.vehicle_speed_m_s
        pedal = state.accelerator_pedal_position
        throttle = state.throttle_position

        if (
            speed is not None
            and speed < cls._IDLE_SPEED_M_S
            and pedal is not None
            and pedal < cls._IDLE_PEDAL_MAX
        ):
            return EngineOperatingMode.IDLE

        if high_load is True:
            return EngineOperatingMode.HIGH_LOAD

        if (
            (pedal is not None and pedal >= cls._ACCELERATOR_THRESHOLD)
            or (throttle is not None and throttle >= cls._THROTTLE_THRESHOLD)
        ):
            return EngineOperatingMode.ACCELERATION

        if (
            speed is not None
            and speed >= cls._CRUISE_SPEED_M_S
            and pedal is not None
            and pedal < cls._CRUISE_PEDAL_MAX
            and high_load is not True
        ):
            return EngineOperatingMode.CRUISE

        return EngineOperatingMode.UNKNOWN

    @staticmethod
    def _fuel_control_mode(status: int | None) -> FuelControlMode:
        if status is None:
            return FuelControlMode.UNKNOWN
        return {
            0x01: FuelControlMode.OPEN_LOOP_WARMUP,
            0x02: FuelControlMode.CLOSED_LOOP,
            0x04: FuelControlMode.OPEN_LOOP_LOAD_OR_DECEL,
            0x08: FuelControlMode.OPEN_LOOP_FAULT,
            0x10: FuelControlMode.CLOSED_LOOP_FAULT,
        }.get(status, FuelControlMode.UNKNOWN)

    @staticmethod
    def _sum_optional(first: float | None, second: float | None) -> float | None:
        if first is None or second is None:
            return None
        return first + second

    @staticmethod
    def _difference_optional(
        actual: float | None,
        commanded: float | None,
    ) -> float | None:
        if actual is None or commanded is None:
            return None
        return actual - commanded
