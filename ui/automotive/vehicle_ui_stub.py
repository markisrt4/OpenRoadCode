# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Concrete no-op vehicle telemetry UI implementation."""

from ui.automotive.vehicle_ui_if import Gear, VehicleUiIf


class VehicleUiStub(VehicleUiIf):
    """Ignore independently updated vehicle measurements."""

    def set_gear(self, gear: Gear | None) -> None:
        pass

    def set_vehicle_speed(self, speed_mps: float | None) -> None:
        pass

    def set_engine_speed(self, engine_speed_rad_s: float | None) -> None:
        pass

    def set_fuel_level(self, fuel_level_ratio: float | None) -> None:
        pass

    def set_throttle_position(
        self,
        throttle_position_ratio: float | None,
    ) -> None:
        pass

    def set_accelerator_position(
        self,
        accelerator_position_ratio: float | None,
    ) -> None:
        pass

    def set_engine_load(self, engine_load_ratio: float | None) -> None:
        pass

    def set_coolant_temperature(
        self,
        coolant_temperature_k: float | None,
    ) -> None:
        pass

    def set_intake_air_temperature(
        self,
        intake_air_temperature_k: float | None,
    ) -> None:
        pass

    def set_manifold_pressure(
        self,
        manifold_pressure_pa: float | None,
    ) -> None:
        pass

    def set_barometric_pressure(
        self,
        barometric_pressure_pa: float | None,
    ) -> None:
        pass

    def set_boost_pressure(self, boost_pressure_pa: float | None) -> None:
        pass

    def set_mass_air_flow(self, mass_air_flow_kg_s: float | None) -> None:
        pass

    def set_control_voltage(self, control_voltage_v: float | None) -> None:
        pass

    def set_ambient_temperature(self, ambient_temperature_k: float | None) -> None:
        pass

    def set_engine_oil_temperature(
        self,
        engine_oil_temperature_k: float | None,
    ) -> None:
        pass

    def set_engine_oil_pressure(
        self,
        engine_oil_pressure_pa: float | None,
    ) -> None:
        pass

    def set_transmission_temperature(
        self,
        transmission_temperature_k: float | None,
    ) -> None:
        pass
