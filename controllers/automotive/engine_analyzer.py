# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

from controllers.automotive.engine_analysis import (
    EngineAnalysis,
    EngineLoadLevel,
    EngineOperatingMode,
    FuelControlMode,
    FuelCorrectionStatus,
    MixtureMode,
    TrackingQuality,
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
    _MIXTURE_BAND = 0.03
    _TRACKING_GOOD = 0.03
    _TRACKING_MODERATE = 0.08
    _FUEL_CORRECTION_NORMAL = 0.05
    _LOAD_LOW = 0.35

    def __init__(self, configuration: VehicleConfiguration) -> None:
        self._configuration = configuration

    def analyze(self, state: VehicleState) -> EngineAnalysis:
        engine_running = self._engine_running(state)
        warmed_up = self._warmed_up(state)
        high_load = self._high_load(state)
        enrichment = self._enrichment_active(state)
        forced_induction = self._forced_induction_active(state)

        fuel_trim_total = self._sum_optional(
            state.short_term_fuel_trim_bank1,
            state.long_term_fuel_trim_bank1,
        )
        mixture_error = self._difference_optional(
            state.measured_equivalence_ratio,
            state.commanded_equivalence_ratio,
        )
        throttle_error = self._difference_optional(
            state.throttle_position,
            state.commanded_throttle_position,
        )

        return EngineAnalysis(
            operating_mode=self._operating_mode(
                state,
                engine_running=engine_running,
            ),
            fuel_control_mode=self._fuel_control_mode(state.fuel_system_status_1),
            mixture_mode=self._mixture_mode(state.commanded_equivalence_ratio),
            mixture_tracking=self._tracking_quality(mixture_error),
            throttle_tracking=self._tracking_quality(throttle_error),
            fuel_correction_status=self._fuel_correction_status(fuel_trim_total),
            load_level=self._load_level(state),
            engine_running=engine_running,
            warmed_up=warmed_up,
            enrichment_active=enrichment,
            high_load=high_load,
            forced_induction_active=forced_induction,
            fuel_trim_total=fuel_trim_total,
            mixture_tracking_error=mixture_error,
            throttle_tracking_error=throttle_error,
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
        ):
            return EngineOperatingMode.CRUISE

        return EngineOperatingMode.UNKNOWN

    @classmethod
    def _mixture_mode(cls, commanded_lambda: float | None) -> MixtureMode:
        if commanded_lambda is None:
            return MixtureMode.UNKNOWN
        if commanded_lambda < 1.0 - cls._MIXTURE_BAND:
            return MixtureMode.RICH
        if commanded_lambda > 1.0 + cls._MIXTURE_BAND:
            return MixtureMode.LEAN
        return MixtureMode.STOICHIOMETRIC

    @classmethod
    def _tracking_quality(cls, error: float | None) -> TrackingQuality:
        if error is None:
            return TrackingQuality.UNKNOWN
        magnitude = abs(error)
        if magnitude <= cls._TRACKING_GOOD:
            return TrackingQuality.GOOD
        if magnitude <= cls._TRACKING_MODERATE:
            return TrackingQuality.MODERATE
        return TrackingQuality.POOR

    @classmethod
    def _fuel_correction_status(
        cls,
        total: float | None,
    ) -> FuelCorrectionStatus:
        if total is None:
            return FuelCorrectionStatus.UNKNOWN
        if abs(total) <= cls._FUEL_CORRECTION_NORMAL:
            return FuelCorrectionStatus.NORMAL
        if total > 0.0:
            return FuelCorrectionStatus.ADDING_FUEL
        return FuelCorrectionStatus.REMOVING_FUEL

    @classmethod
    def _load_level(cls, state: VehicleState) -> EngineLoadLevel:
        load = (
            state.absolute_engine_load
            if state.absolute_engine_load is not None
            else state.engine_load
        )
        if load is None:
            return EngineLoadLevel.UNKNOWN
        if load >= cls._HIGH_LOAD_THRESHOLD:
            return EngineLoadLevel.HIGH
        if load < cls._LOAD_LOW:
            return EngineLoadLevel.LOW
        return EngineLoadLevel.MODERATE

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
