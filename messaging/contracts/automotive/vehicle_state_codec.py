import math
from typing import Any
from controllers.automotive.vehicle_state import VehicleState

SCHEMA_VERSION = 1

def _convert(value, fn):
    return None if value is None else fn(value)

def encode_vehicle_state(state: VehicleState, *, source: str = "obd2") -> dict[str, Any]:
    return {
        "version": SCHEMA_VERSION,
        "timestamp": state.timestamp.isoformat(),
        "source": source,
        "data": {
            "engine_speed_rad_s": _convert(state.rpm, lambda v: v * 2.0 * math.pi / 60.0),
            "vehicle_speed_m_s": _convert(state.speed_mph, lambda v: v * 0.44704),
            "throttle_position": _convert(state.throttle_pct, lambda v: v / 100.0),
            "accelerator_pedal_position": _convert(state.accelerator_pedal_pct, lambda v: v / 100.0),
            "engine_load": _convert(state.engine_load_pct, lambda v: v / 100.0),
            "intake_manifold_pressure_pa": _convert(state.map_kpa, lambda v: v * 1000),
            "barometric_pressure_pa": _convert(state.baro_kpa, lambda v: v * 1000),
            "boost_pressure_pa": _convert(state.boost_psi, lambda v: v * 6894.757293168),
            "mass_air_flow_kg_s": _convert(state.maf_gps, lambda v: v / 1000.0),
            "coolant_temperature_k": _convert(state.coolant_temp_f, lambda v: (v - 32.0) * 5.0 / 9.0 + 273.15),
            "intake_air_temperature_k": _convert(state.intake_temp_f, lambda v: (v - 32.0) * 5.0 / 9.0 + 273.15),
            "fuel_level": _convert(state.fuel_level_pct, lambda v: v / 100.0),
            "control_voltage_v": state.control_voltage,
        },
    }
