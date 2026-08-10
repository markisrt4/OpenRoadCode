"""Deterministic software simulation of changing vehicle telemetry."""

from datetime import datetime
import math

from controllers.automotive.vehicle_state import VehicleState
from controllers.automotive.vehicle_state_source_if import VehicleStateSourceIf


class SimulatedVehicleStateSource(VehicleStateSourceIf):
    """Generate plausible vehicle values without OBD-II hardware."""

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
        return VehicleState(
            timestamp=datetime.now(),
            rpm=850.0 + 3200.0 * load,
            speed_mph=8.0 + 52.0 * load,
            throttle_pct=10.0 + 65.0 * load,
            accelerator_pedal_pct=8.0 + 62.0 * load,
            engine_load_pct=20.0 + 70.0 * load,
            map_kpa=round(45.0 + 95.0 * load),
            baro_kpa=101,
            boost_psi=-8.0 + 15.0 * load,
            maf_gps=3.0 + 28.0 * load,
            coolant_temp_f=188.0 + 8.0 * math.sin(self._phase * 0.25),
            intake_temp_f=72.0 + 6.0 * math.sin(self._phase * 0.4),
            fuel_level_pct=max(0.0, 78.0 - self._phase * 0.03),
            control_voltage=13.8 + 0.2 * math.sin(self._phase * 0.5),
        )
