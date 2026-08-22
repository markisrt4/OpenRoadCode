# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Deterministic software simulation of changing SI vehicle telemetry."""

from datetime import datetime
import math

from controllers.automotive.vehicle_state import VehicleState
from controllers.automotive.vehicle_state_source_if import VehicleStateSourceIf


class SimulatedVehicleStateSource(VehicleStateSourceIf):
    """Generate plausible SI-normalized vehicle values without OBD-II hardware."""

    def __init__(self, step_radians: float = 0.12) -> None:
        self._step_radians = step_radians
        self._phase = 0.0
        self._connected = False

    def connect(self) -> None:
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False

    def read_state(self) -> VehicleState:
        if not self._connected:
            raise RuntimeError("simulated vehicle source is not connected")
        self._phase += self._step_radians
        wave = math.sin(self._phase)
        load = (wave + 1.0) / 2.0
        rpm = 850.0 + 3200.0 * load
        map_pa = (45.0 + 95.0 * load) * 1000.0
        baro_pa = 101000.0
        return VehicleState(
            timestamp=datetime.now(),
            engine_speed_rad_s=rpm * 2.0 * math.pi / 60.0,
            vehicle_speed_m_s=(8.0 + 52.0 * load) * 0.44704,
            throttle_position=(10.0 + 65.0 * load) / 100.0,
            accelerator_pedal_position=(8.0 + 62.0 * load) / 100.0,
            engine_load=(20.0 + 70.0 * load) / 100.0,
            intake_manifold_pressure_pa=map_pa,
            barometric_pressure_pa=baro_pa,
            boost_pressure_pa=map_pa - baro_pa,
            mass_air_flow_kg_s=(3.0 + 28.0 * load) / 1000.0,
            coolant_temperature_k=(188.0 + 8.0 * math.sin(self._phase * 0.25) - 32.0) * 5.0 / 9.0 + 273.15,
            intake_air_temperature_k=(72.0 + 6.0 * math.sin(self._phase * 0.4) - 32.0) * 5.0 / 9.0 + 273.15,
            fuel_level=max(0.0, 78.0 - self._phase * 0.03) / 100.0,
            control_voltage_v=13.8 + 0.2 * math.sin(self._phase * 0.5),
        )
