# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Compose engine telemetry with navigation-owned road speed."""

from __future__ import annotations

from dataclasses import replace

from controllers.automotive.automotive_telemetry_profile import AutomotiveTelemetryProfile
from controllers.automotive.vehicle_state import VehicleState
from controllers.automotive.vehicle_state_source_if import VehicleStateSourceIf


class CompositeVehicleStateSource(VehicleStateSourceIf):
    """Combine an automotive engine source with a road-motion source."""

    def __init__(
        self,
        engine_source: VehicleStateSourceIf,
        motion_source: VehicleStateSourceIf,
    ) -> None:
        self._engine_source = engine_source
        self._motion_source = motion_source

    def connect(self) -> None:
        self._engine_source.connect()
        try:
            self._motion_source.connect()
        except Exception:
            self._engine_source.disconnect()
            raise

    def disconnect(self) -> None:
        try:
            self._motion_source.disconnect()
        finally:
            self._engine_source.disconnect()

    def set_telemetry_profile(self, profile: AutomotiveTelemetryProfile) -> None:
        """Forward telemetry-priority hints to the engine source when supported."""
        setter = getattr(self._engine_source, "set_telemetry_profile", None)
        if callable(setter):
            setter(profile)

    def read_state(self) -> VehicleState:
        engine = self._engine_source.read_state()
        motion = self._motion_source.read_state()
        return replace(
            engine,
            vehicle_speed_m_s=motion.vehicle_speed_m_s,
        )
