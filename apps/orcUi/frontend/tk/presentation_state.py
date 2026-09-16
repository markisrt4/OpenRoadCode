# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Presentation-state ownership for the integrated orcUi shell."""

from __future__ import annotations

from dataclasses import dataclass, field

from apps.orcUi.navigation_presenter import (
    AttitudePresentationState,
    PositionPresentationState,
)
from apps.orcUi.trip_presenter import TripPresentationState
from apps.orcUi.vehicle_presenter import VehiclePresentationState
from controllers.automotive import (
    EngineAnalysis,
    EngineLoadLevel,
    EngineOperatingMode,
    FuelControlMode,
    FuelCorrectionStatus,
    MixtureMode,
    TrackingQuality,
)


def _empty_engine_analysis() -> EngineAnalysis:
    return EngineAnalysis(
        operating_mode=EngineOperatingMode.UNKNOWN,
        fuel_control_mode=FuelControlMode.UNKNOWN,
        mixture_mode=MixtureMode.UNKNOWN,
        mixture_tracking=TrackingQuality.UNKNOWN,
        throttle_tracking=TrackingQuality.UNKNOWN,
        fuel_correction_status=FuelCorrectionStatus.UNKNOWN,
        load_level=EngineLoadLevel.UNKNOWN,
        engine_running=None,
        warmed_up=None,
        enrichment_active=None,
        high_load=None,
        forced_induction_active=None,
        fuel_trim_total=None,
        mixture_tracking_error=None,
        throttle_tracking_error=None,
    )


@dataclass
class OrcUiPresentationState:
    """Hold the latest presented state independent of mounted Tk widgets."""

    vehicle: VehiclePresentationState = field(default_factory=VehiclePresentationState)
    trip: TripPresentationState = field(default_factory=TripPresentationState)
    position: PositionPresentationState = field(default_factory=PositionPresentationState)
    attitude: AttitudePresentationState = field(default_factory=AttitudePresentationState)
    engine_analysis: EngineAnalysis = field(default_factory=_empty_engine_analysis)

    def apply_vehicle(self, state: VehiclePresentationState, *, context, vehicle_panel) -> None:
        self.vehicle = state
        if context is not None and context.winfo_exists():
            context.update_vehicle_state(state)
        if vehicle_panel is not None and vehicle_panel.winfo_exists():
            vehicle_panel.update_state(state)

    def apply_trip(self, state: TripPresentationState, *, context, vehicle_panel) -> None:
        self.trip = state
        if context is not None and context.winfo_exists():
            context.update_trip_state(state)
        if vehicle_panel is not None and vehicle_panel.winfo_exists():
            vehicle_panel.update_trip_state(state)

    def apply_position(self, state: PositionPresentationState, *, context, offroad_panel) -> None:
        self.position = state
        if context is not None and context.winfo_exists():
            context.update_position_state(state)
        if offroad_panel is not None and offroad_panel.winfo_exists():
            offroad_panel.update_position(state)

    def apply_attitude(self, state: AttitudePresentationState, *, context, offroad_panel) -> None:
        self.attitude = state
        if context is not None and context.winfo_exists():
            context.update_attitude_state(state)
        if offroad_panel is not None and offroad_panel.winfo_exists():
            offroad_panel.update_attitude(state)

    def apply_engine_analysis(self, analysis: EngineAnalysis, *, vehicle_panel) -> None:
        self.engine_analysis = analysis
        if vehicle_panel is not None and vehicle_panel.winfo_exists():
            vehicle_panel.update_engine_analysis(analysis)
