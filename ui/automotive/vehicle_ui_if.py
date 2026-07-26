from ..ui_if import UiIf
from abc import ABC, abstractmethod

class VehicleUiIf(UiIf, ABC):
    
    @abstractmethod
    def set_vehicle_speed(self, kph: float) -> None:
        """
        Set the vehicle speed in km/h.
        """
        ...
        
    @abstractmethod
    def set_vehicle_rpm(self, rpm: float) -> None:
        """
        Set the vehicle RPM.
        """
        ...
        
    @abstractmethod
    def set_vehicle_fuel_level(self, fuel_level_pct: float) -> None:
        """
        Set the vehicle fuel level in percentage.
        """
        ...
        
    @abstractmethod
    def set_vehicle_coolant_temp(self, coolant_temp_f: float) -> None:
        """
        Set the vehicle coolant temperature in Fahrenheit.
        """
        ...
        
    @abstractmethod
    def set_throttle_position(self, throttle_pct: float) -> None:
        """
        Set the vehicle throttle position in percentage.
        """
        ...
    
    @abstractmethod
    def set_accelerator_pedal_position(self, accelerator_pedal_pct: float) -> None:
        """
        Set the vehicle accelerator pedal position in percentage.
        """
        ...
        
    @abstractmethod
    def set_engine_load(self, engine_load_pct: float) -> None:
        """
        Set the vehicle engine load in percentage.
        """
        ...
        
    @abstractmethod
    def set_map_pressure(self, map_kpa: int) -> None:
        """
        Set the vehicle manifold absolute pressure in kPa.
        """
        ...
        
    @abstractmethod
    def set_baro_pressure(self, baro_kpa: int) -> None:
        """
        Set the vehicle barometric pressure in kPa.
        """
        ...
        
    @abstractmethod
    def set_boost_pressure(self, boost_psi: float) -> None:
        """
        Set the vehicle boost pressure in psi.
        """
        ...
