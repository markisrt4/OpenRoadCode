"""! @brief UI contract for vehicle distance and fuel-use information."""

from abc import ABC, abstractmethod

from ..ui_if import UiIf


class VehicleTripUiIf(UiIf, ABC):
    """! @brief Display independently updated trip measurements in SI units."""

    @abstractmethod
    def set_odometer(self, distance_m: float | None) -> None:
        """! @brief Set the vehicle's lifetime distance.

        @param distance_m Lifetime distance in metres, or None.
        """
        ...

    @abstractmethod
    def set_trip_distance(self, distance_m: float | None) -> None:
        """! @brief Set the current trip distance.

        @param distance_m Trip distance in metres, or None.
        """
        ...

    @abstractmethod
    def set_estimated_range(self, distance_m: float | None) -> None:
        """! @brief Set the estimated remaining driving range.

        @param distance_m Estimated range in metres, or None.
        """
        ...

    @abstractmethod
    def set_instantaneous_fuel_consumption(
        self,
        fuel_consumption_m3_per_m: float | None,
    ) -> None:
        """! @brief Set instantaneous fuel volume consumed per distance.

        @param fuel_consumption_m3_per_m Cubic metres per metre, or None.
        """
        ...

    @abstractmethod
    def set_average_fuel_consumption(
        self,
        fuel_consumption_m3_per_m: float | None,
    ) -> None:
        """! @brief Set average fuel volume consumed per distance.

        @param fuel_consumption_m3_per_m Cubic metres per metre, or None.
        """
        ...

    @abstractmethod
    def set_fuel_used(self, fuel_volume_m3: float | None) -> None:
        """! @brief Set fuel consumed during the current trip.

        @param fuel_volume_m3 Fuel volume in cubic metres, or None.
        """
        ...
