"""Concrete no-op vehicle tire UI implementation."""

from ui.automotive.vehicle_tire_ui_if import TirePosition, VehicleTireUiIf
from ui.ui_stub import UiStub


class VehicleTireUiStub(UiStub, VehicleTireUiIf):
    """Ignore vehicle tire updates."""

    def set_tire_pressure(
        self,
        position: TirePosition,
        pressure_pa: float | None,
    ) -> None:
        pass

    def set_tire_temperature(
        self,
        position: TirePosition,
        temperature_k: float | None,
    ) -> None:
        pass

    def set_tire_pressure_warning(
        self,
        position: TirePosition,
        active: bool | None,
    ) -> None:
        pass
