# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Compose engine telemetry with navigation-owned road motion."""

from __future__ import annotations

from dataclasses import replace

from controllers.automotive.vehicle_state import VehicleState
from controllers.automotive.vehicle_state_source_if import VehicleStateSourceIf


class CompositeVehicleStateSource(VehicleStateSourceIf):
    """Merge a complete vehicle source with a preferred motion source.

    Engine, pressure, temperature, fuel, and related vehicle telemetry come
    from ``vehicle_source``. Navigation ground speed overrides the vehicle
    source's speed when available, preserving navigation as the owner of road
    motion while still allowing OBD-II speed as a fallback.
    """

    def __init__(
        self,
        vehicle_source: VehicleStateSourceIf,
        motion_source: VehicleStateSourceIf,
    ) -> None:
        self._vehicle_source = vehicle_source
        self._motion_source = motion_source

    def connect(self) -> None:
        """Connect both underlying sources."""
        self._vehicle_source.connect()
        try:
            self._motion_source.connect()
        except Exception:
            self._vehicle_source.disconnect()
            raise

    def disconnect(self) -> None:
        """Disconnect both underlying sources."""
        try:
            self._motion_source.disconnect()
        finally:
            self._vehicle_source.disconnect()

    def read_state(self) -> VehicleState:
        """Return vehicle telemetry with navigation speed when available."""
        vehicle_state = self._vehicle_source.read_state()
        motion_state = self._motion_source.read_state()
        if motion_state.vehicle_speed_m_s is None:
            return vehicle_state
        return replace(
            vehicle_state,
            vehicle_speed_m_s=motion_state.vehicle_speed_m_s,
        )
