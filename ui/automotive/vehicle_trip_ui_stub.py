"""Concrete no-op vehicle trip UI implementation."""

from ui.automotive.vehicle_trip_ui_if import VehicleTripUiIf


class VehicleTripUiStub(VehicleTripUiIf):
    """Ignore vehicle trip updates."""

    def set_odometer(self, distance_m: float | None) -> None:
        pass

    def set_trip_distance(self, distance_m: float | None) -> None:
        pass

    def set_estimated_range(self, distance_m: float | None) -> None:
        pass

    def set_instantaneous_fuel_consumption(
        self,
        fuel_consumption_m3_per_m: float | None,
    ) -> None:
        pass

    def set_average_fuel_consumption(
        self,
        fuel_consumption_m3_per_m: float | None,
    ) -> None:
        pass

    def set_fuel_used(self, fuel_volume_m3: float | None) -> None:
        pass
