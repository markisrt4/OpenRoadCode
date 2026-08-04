"""! @brief Explicit UI contract for independently updated vehicle telemetry."""

from abc import ABC, abstractmethod
from enum import Enum, auto

from ..ui_if import UiIf


class Gear(Enum):
    """! @brief Gear currently engaged by the vehicle."""

    REVERSE = auto()
    NEUTRAL = auto()
    FIRST = auto()
    SECOND = auto()
    THIRD = auto()
    FOURTH = auto()
    FIFTH = auto()
    SIXTH = auto()


class VehicleUiIf(UiIf, ABC):
    """! @brief Display independently updated vehicle measurements.

    Physical measurements use SI units. Dimensionless ratios use the inclusive
    range 0.0 through 1.0. ``None`` means an individual measurement is
    currently unavailable or unsupported. Implementations are responsible for
    converting values to the units selected by the user.
    """

    @abstractmethod
    def set_gear(self, gear: Gear | None) -> None:
        """! @brief Set the currently engaged gear.

        @param gear Current gear, or None when unavailable.
        """
        ...

    @abstractmethod
    def set_vehicle_speed(self, speed_mps: float | None) -> None:
        """! @brief Set vehicle speed.

        @param speed_mps Vehicle speed in metres per second, or None.
        """
        ...

    @abstractmethod
    def set_engine_speed(self, engine_speed_rad_s: float | None) -> None:
        """! @brief Set engine angular speed.

        @param engine_speed_rad_s Engine speed in radians per second, or None.
        """
        ...

    @abstractmethod
    def set_fuel_level(self, fuel_level_ratio: float | None) -> None:
        """! @brief Set fuel level.

        @param fuel_level_ratio Fuel level from 0.0 through 1.0, or None.
        """
        ...

    @abstractmethod
    def set_throttle_position(
        self,
        throttle_position_ratio: float | None,
    ) -> None:
        """! @brief Set throttle position.

        @param throttle_position_ratio Position from 0.0 through 1.0, or None.
        """
        ...

    @abstractmethod
    def set_accelerator_position(
        self,
        accelerator_position_ratio: float | None,
    ) -> None:
        """! @brief Set accelerator-pedal position.

        @param accelerator_position_ratio Position from 0.0 through 1.0, or None.
        """
        ...

    @abstractmethod
    def set_engine_load(self, engine_load_ratio: float | None) -> None:
        """! @brief Set calculated engine load.

        @param engine_load_ratio Engine load from 0.0 through 1.0, or None.
        """
        ...

    @abstractmethod
    def set_coolant_temperature(
        self,
        coolant_temperature_k: float | None,
    ) -> None:
        """! @brief Set engine coolant temperature.

        @param coolant_temperature_k Temperature in kelvin, or None.
        """
        ...

    @abstractmethod
    def set_intake_air_temperature(
        self,
        intake_air_temperature_k: float | None,
    ) -> None:
        """! @brief Set intake-air temperature.

        @param intake_air_temperature_k Temperature in kelvin, or None.
        """
        ...

    @abstractmethod
    def set_manifold_pressure(
        self,
        manifold_pressure_pa: float | None,
    ) -> None:
        """! @brief Set manifold absolute pressure.

        @param manifold_pressure_pa Absolute pressure in pascals, or None.
        """
        ...

    @abstractmethod
    def set_barometric_pressure(
        self,
        barometric_pressure_pa: float | None,
    ) -> None:
        """! @brief Set ambient barometric pressure.

        @param barometric_pressure_pa Pressure in pascals, or None.
        """
        ...

    @abstractmethod
    def set_boost_pressure(self, boost_pressure_pa: float | None) -> None:
        """! @brief Set boost pressure relative to atmosphere.

        @param boost_pressure_pa Relative pressure in pascals, or None.
        """
        ...

    @abstractmethod
    def set_mass_air_flow(self, mass_air_flow_kg_s: float | None) -> None:
        """! @brief Set engine mass air flow.

        @param mass_air_flow_kg_s Mass flow in kilograms per second, or None.
        """
        ...

    @abstractmethod
    def set_control_voltage(self, control_voltage_v: float | None) -> None:
        """! @brief Set vehicle control-module voltage.

        @param control_voltage_v Voltage in volts, or None.
        """
        ...

    @abstractmethod
    def set_ambient_temperature(self, ambient_temperature_k: float | None) -> None:
        """! @brief Set the outside ambient temperature.

        @param ambient_temperature_k Temperature in kelvin, or None.
        """
        ...

    @abstractmethod
    def set_engine_oil_temperature(
        self,
        engine_oil_temperature_k: float | None,
    ) -> None:
        """! @brief Set the engine oil temperature.

        @param engine_oil_temperature_k Temperature in kelvin, or None.
        """
        ...

    @abstractmethod
    def set_engine_oil_pressure(
        self,
        engine_oil_pressure_pa: float | None,
    ) -> None:
        """! @brief Set the engine oil pressure.

        @param engine_oil_pressure_pa Pressure in pascals, or None.
        """
        ...

    @abstractmethod
    def set_transmission_temperature(
        self,
        transmission_temperature_k: float | None,
    ) -> None:
        """! @brief Set the transmission-fluid temperature.

        @param transmission_temperature_k Temperature in kelvin, or None.
        """
        ...
