# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Thread-safe vehicle contract cache for the main Car TUI."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock

from controllers.automotive import VehicleState
from messaging.contracts.automotive import VehicleStateMessage


@dataclass(frozen=True, slots=True)
class VehicleBusSnapshot:
    """Latest vehicle state and bus diagnostics for a TUI consumer."""

    state: VehicleState | None
    source: str | None
    received_count: int
    error: str | None

    @property
    def connected(self) -> bool:
        return self.state is not None and self.error is None

    @property
    def status(self) -> str:
        if self.error is not None:
            return self.error
        if self.state is None:
            return "Waiting for vehicle telemetry"
        return f"Live {self.source} · {self.received_count} messages"


class VehicleBusState:
    """Convert vehicle bus messages into the domain snapshot used by the TUI."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._state: VehicleState | None = None
        self._source: str | None = None
        self._received_count = 0
        self._error: str | None = None

    def set_vehicle(self, message: VehicleStateMessage) -> None:
        timestamp = datetime.fromtimestamp(
            message.timestamp.seconds + message.timestamp.nanoseconds / 1_000_000_000.0,
            tz=timezone.utc,
        )
        data = message.data
        state = VehicleState(
            timestamp=timestamp,
            engine_speed_rad_s=data.engine_speed_rad_s,
            vehicle_speed_m_s=data.vehicle_speed_m_s,
            throttle_position=data.throttle_position,
            accelerator_pedal_position=data.accelerator_pedal_position,
            engine_load=data.engine_load,
            intake_manifold_pressure_pa=data.intake_manifold_pressure_pa,
            barometric_pressure_pa=data.barometric_pressure_pa,
            boost_pressure_pa=data.boost_pressure_pa,
            mass_air_flow_kg_s=data.mass_air_flow_kg_s,
            coolant_temperature_k=data.coolant_temperature_k,
            intake_air_temperature_k=data.intake_air_temperature_k,
            fuel_level=data.fuel_level,
            control_voltage_v=data.control_voltage_v,
        )
        with self._lock:
            self._state = state
            self._source = message.source
            self._received_count += 1
            self._error = None

    def set_error(self, topic: str, error: Exception) -> None:
        with self._lock:
            self._error = f"Vehicle bus error [{topic}]: {type(error).__name__}: {error}"

    def snapshot(self) -> VehicleBusSnapshot:
        with self._lock:
            return VehicleBusSnapshot(
                state=self._state,
                source=self._source,
                received_count=self._received_count,
                error=self._error,
            )
