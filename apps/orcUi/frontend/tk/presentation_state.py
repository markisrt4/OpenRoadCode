# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Presentation-state ownership for the integrated orcUi shell."""

from __future__ import annotations

from collections.abc import Callable
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
    _vehicle_observers: list[Callable[[VehiclePresentationState], None]] = field(
        default_factory=list,
        init=False,
        repr=False,
    )
    _trip_observers: list[Callable[[TripPresentationState], None]] = field(
        default_factory=list,
        init=False,
        repr=False,
    )
    _position_observers: list[Callable[[PositionPresentationState], None]] = field(
        default_factory=list,
        init=False,
        repr=False,
    )
    _attitude_observers: list[Callable[[AttitudePresentationState], None]] = field(
        default_factory=list,
        init=False,
        repr=False,
    )

    def observe_vehicle(
        self,
        observer: Callable[[VehiclePresentationState], None],
    ) -> None:
        """Subscribe to future vehicle presentation updates."""
        self._vehicle_observers.append(observer)

    def observe_trip(
        self,
        observer: Callable[[TripPresentationState], None],
    ) -> None:
        """Subscribe to future trip presentation updates."""
        self._trip_observers.append(observer)

    def observe_position(
        self,
        observer: Callable[[PositionPresentationState], None],
    ) -> None:
        """Subscribe to future position presentation updates."""
        self._position_observers.append(observer)

    def observe_attitude(
        self,
        observer: Callable[[AttitudePresentationState], None],
    ) -> None:
        """Subscribe to future attitude presentation updates."""
        self._attitude_observers.append(observer)

    def apply_vehicle(self, state: VehiclePresentationState, *, vehicle_panel) -> None:
        self.vehicle = state
        if vehicle_panel is not None and vehicle_panel.winfo_exists():
            vehicle_panel.update_state(state)
        for observer in tuple(self._vehicle_observers):
            observer(state)

    def apply_trip(self, state: TripPresentationState, *, vehicle_panel) -> None:
        self.trip = state
        if vehicle_panel is not None and vehicle_panel.winfo_exists():
            vehicle_panel.update_trip_state(state)
        for observer in tuple(self._trip_observers):
            observer(state)

    def apply_position(self, state: PositionPresentationState, *, offroad_panel) -> None:
        self.position = state
        if offroad_panel is not None and offroad_panel.winfo_exists():
            offroad_panel.update_position(state)
        for observer in tuple(self._position_observers):
            observer(state)

    def apply_attitude(self, state: AttitudePresentationState, *, offroad_panel) -> None:
        self.attitude = state
        if offroad_panel is not None and offroad_panel.winfo_exists():
            offroad_panel.update_attitude(state)
        for observer in tuple(self._attitude_observers):
            observer(state)

    def apply_engine_analysis(self, analysis: EngineAnalysis, *, vehicle_panel) -> None:
        self.engine_analysis = analysis
        if vehicle_panel is not None and vehicle_panel.winfo_exists():
            vehicle_panel.update_engine_analysis(analysis)
