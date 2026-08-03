"""Concrete no-op vehicle telemetry UI implementation."""

from ui.automotive.vehicle_ui_if import VehicleUiIf
from ui.ui_stub import UiStub


class VehicleUiStub(UiStub, VehicleUiIf):
    """Ignore vehicle telemetry display updates."""

    def set_vehicle_speed(self, kph: float) -> None:
        pass

    def set_vehicle_rpm(self, rpm: float) -> None:
        pass

    def set_vehicle_fuel_level(self, fuel_level_pct: float) -> None:
        pass

    def set_vehicle_coolant_temp(self, coolant_temp_f: float) -> None:
        pass

    def set_throttle_position(self, throttle_pct: float) -> None:
        pass

    def set_accelerator_pedal_position(self, accelerator_pedal_pct: float) -> None:
        pass

    def set_engine_load(self, engine_load_pct: float) -> None:
        pass

    def set_map_pressure(self, map_kpa: int) -> None:
        pass

    def set_baro_pressure(self, baro_kpa: int) -> None:
        pass

    def set_boost_pressure(self, boost_psi: float) -> None:
        pass
