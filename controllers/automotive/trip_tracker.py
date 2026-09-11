# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Derived automotive trip tracker."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime

from controllers.automotive.fuel_model import FuelModel
from controllers.automotive.trip_if import TripIf
from controllers.automotive.trip_state import TripState, TripStatus
from controllers.automotive.vehicle_state import VehicleState
from controllers.navigation.navigation_state import GroundMotionState, PositionState


class TripTracker(TripIf):
    """Accumulate normalized observations into an immutable trip snapshot."""

    def __init__(
        self,
        *,
        moving_threshold_m_s: float = 0.5,
        pause_after_s: float = 3.0,
        fuel_model: FuelModel | None = None,
    ) -> None:
        if moving_threshold_m_s < 0.0:
            raise ValueError("moving_threshold_m_s must not be negative")
        if pause_after_s < 0.0:
            raise ValueError("pause_after_s must not be negative")
        self._moving_threshold_m_s = moving_threshold_m_s
        self._pause_after_s = pause_after_s
        self._fuel_model = fuel_model or FuelModel()
        self.reset()

    def observe_vehicle_state(self, state: VehicleState) -> None:
        """Consume vehicle speed and fuel-flow telemetry when available."""
        if state.vehicle_speed_m_s is not None:
            self._observe_speed(state.timestamp, state.vehicle_speed_m_s)
        self._observe_fuel(
            state.timestamp,
            self._fuel_model.fuel_flow_m3_s(state),
            state.vehicle_speed_m_s,
        )

    def observe_position_state(self, state: PositionState) -> None:
        """Capture usable geographic position independently of motion."""
        if not state.has_fix or state.latitude_deg is None or state.longitude_deg is None:
            return

        if self._state.started_at is None:
            self._pending_position = (state.latitude_deg, state.longitude_deg)
            return

        start_lat = self._state.start_latitude_deg
        start_lon = self._state.start_longitude_deg
        if start_lat is None or start_lon is None:
            start_lat, start_lon = state.latitude_deg, state.longitude_deg

        self._state = replace(
            self._state,
            start_latitude_deg=start_lat,
            start_longitude_deg=start_lon,
            current_latitude_deg=state.latitude_deg,
            current_longitude_deg=state.longitude_deg,
        )

    def observe_ground_motion_state(self, state: GroundMotionState) -> None:
        """Consume provider-neutral ground speed when available."""
        if state.speed_mps is not None:
            self._observe_speed(state.received_at, state.speed_mps)

    def snapshot(self) -> TripState:
        """Return the current immutable trip snapshot."""
        return self._state

    def finish(self, ended_at: datetime | None = None) -> TripState:
        """Finish the current trip and retain its final snapshot."""
        if self._state.status is TripStatus.IDLE:
            return self._state
        if self._state.status is TripStatus.COMPLETE:
            return self._state

        final_time = ended_at or self._last_sample_at or self._state.started_at
        self._state = replace(
            self._state,
            status=TripStatus.COMPLETE,
            ended_at=final_time,
            end_latitude_deg=self._state.current_latitude_deg,
            end_longitude_deg=self._state.current_longitude_deg,
        )
        return self._state

    def reset(self) -> None:
        """Discard current trip state and return to idle."""
        self._state = TripState()
        self._last_sample_at: datetime | None = None
        self._last_speed_m_s: float | None = None
        self._pending_position: tuple[float, float] | None = None
        self._stationary_since: datetime | None = None
        self._last_fuel_sample_at: datetime | None = None
        self._last_fuel_flow_m3_s: float | None = None

    def _observe_speed(self, timestamp: datetime, speed_m_s: float) -> None:
        speed = max(0.0, speed_m_s)
        moving = speed >= self._moving_threshold_m_s

        if self._state.status is TripStatus.IDLE:
            if not moving:
                self._last_sample_at = timestamp
                self._last_speed_m_s = speed
                return
            self._start(timestamp)

        if self._state.status is TripStatus.COMPLETE:
            return

        if self._last_sample_at is not None:
            dt_s = (timestamp - self._last_sample_at).total_seconds()
            if dt_s > 0.0:
                previous_speed = self._last_speed_m_s if self._last_speed_m_s is not None else speed
                interval_distance_m = 0.5 * (previous_speed + speed) * dt_s
                interval_moving = previous_speed >= self._moving_threshold_m_s or moving

                moving_s = self._state.moving_s + (dt_s if interval_moving else 0.0)
                stopped_s = self._state.stopped_s + (0.0 if interval_moving else dt_s)
                distance_m = self._state.distance_m + interval_distance_m

                self._state = replace(
                    self._state,
                    elapsed_s=self._state.elapsed_s + dt_s,
                    moving_s=moving_s,
                    stopped_s=stopped_s,
                    distance_m=distance_m,
                    average_speed_m_s=(
                        distance_m / moving_s if moving_s > 0.0 else None
                    ),
                )

        maximum = self._state.maximum_speed_m_s
        if maximum is None or speed > maximum:
            maximum = speed

        if moving:
            self._stationary_since = None
            status = TripStatus.ACTIVE
        else:
            if self._stationary_since is None:
                self._stationary_since = timestamp
            stationary_s = (timestamp - self._stationary_since).total_seconds()
            status = (
                TripStatus.PAUSED
                if stationary_s >= self._pause_after_s
                else TripStatus.ACTIVE
            )

        self._state = replace(
            self._state,
            status=status,
            maximum_speed_m_s=maximum,
        )
        self._last_sample_at = timestamp
        self._last_speed_m_s = speed


    def _observe_fuel(
        self,
        timestamp: datetime,
        fuel_flow_m3_s: float | None,
        speed_m_s: float | None,
    ) -> None:
        if fuel_flow_m3_s is None or self._state.status is TripStatus.IDLE:
            return
        flow = max(0.0, fuel_flow_m3_s)
        fuel_used = self._state.fuel_used_m3 or 0.0

        if self._last_fuel_sample_at is not None and self._last_fuel_flow_m3_s is not None:
            dt_s = (timestamp - self._last_fuel_sample_at).total_seconds()
            if dt_s > 0.0:
                fuel_used += 0.5 * (self._last_fuel_flow_m3_s + flow) * dt_s

        instantaneous = None
        if speed_m_s is not None and speed_m_s > self._moving_threshold_m_s and flow > 0.0:
            instantaneous = flow / speed_m_s

        average = None
        if self._state.distance_m > 0.0 and fuel_used > 0.0:
            average = fuel_used / self._state.distance_m

        self._state = replace(
            self._state,
            fuel_used_m3=fuel_used,
            instantaneous_fuel_consumption_m3_per_m=instantaneous,
            average_fuel_consumption_m3_per_m=average,
        )
        self._last_fuel_sample_at = timestamp
        self._last_fuel_flow_m3_s = flow

    def _start(self, timestamp: datetime) -> None:
        latitude = longitude = None
        if self._pending_position is not None:
            latitude, longitude = self._pending_position

        self._state = TripState(
            status=TripStatus.ACTIVE,
            started_at=timestamp,
            start_latitude_deg=latitude,
            start_longitude_deg=longitude,
            current_latitude_deg=latitude,
            current_longitude_deg=longitude,
        )
        self._last_sample_at = timestamp
        self._last_speed_m_s = 0.0
