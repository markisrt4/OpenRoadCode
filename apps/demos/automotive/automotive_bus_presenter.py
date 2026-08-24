# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Present public automotive bus messages through the demo UI contracts."""

from __future__ import annotations

from messaging.contracts.automotive.vehicle_state_message import VehicleStateMessage
from ui.automotive import VehicleConnectionState


class AutomotiveBusPresenter:
    """Map decoded vehicle-state messages onto the existing demo UI setters."""

    def __init__(self, ui) -> None:
        self._ui = ui

    def set_vehicle_message(self, message: VehicleStateMessage) -> None:
        data = message.data
        self._ui.set_connection_state(VehicleConnectionState.CONNECTED)
        self._ui.set_vehicle_speed(data.vehicle_speed_m_s)
        self._ui.set_engine_speed(data.engine_speed_rad_s)
        self._ui.set_fuel_level(data.fuel_level)
        self._ui.set_throttle_position(data.throttle_position)
        self._ui.set_accelerator_position(data.accelerator_pedal_position)
        self._ui.set_engine_load(data.engine_load)
        self._ui.set_coolant_temperature(data.coolant_temperature_k)
        self._ui.set_intake_air_temperature(data.intake_air_temperature_k)
        self._ui.set_manifold_pressure(data.intake_manifold_pressure_pa)
        self._ui.set_barometric_pressure(data.barometric_pressure_pa)
        self._ui.set_boost_pressure(data.boost_pressure_pa)
        self._ui.set_mass_air_flow(data.mass_air_flow_kg_s)
        self._ui.set_control_voltage(data.control_voltage_v)

    def set_error(self, _topic: str, _error: Exception) -> None:
        self._ui.set_connection_state(VehicleConnectionState.ERROR)
