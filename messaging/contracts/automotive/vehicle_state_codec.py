from typing import Any

from controllers.automotive.vehicle_state import VehicleState
from messaging.contracts.common import encode_timestamp

SCHEMA_VERSION = 1


def encode_vehicle_state(state: VehicleState, *, source: str = "obd2") -> dict[str, Any]:
    """Encode an already SI-normalized vehicle snapshot."""
    payload = {
        "version": SCHEMA_VERSION,
        "timestamp": encode_timestamp(state.timestamp),
        "source": source,
        "data": {
            "engine_speed_rad_s": state.engine_speed_rad_s,
            "vehicle_speed_m_s": state.vehicle_speed_m_s,
            "throttle_position": state.throttle_position,
            "accelerator_pedal_position": state.accelerator_pedal_position,
            "engine_load": state.engine_load,
            "intake_manifold_pressure_pa": state.intake_manifold_pressure_pa,
            "barometric_pressure_pa": state.barometric_pressure_pa,
            "boost_pressure_pa": state.boost_pressure_pa,
            "mass_air_flow_kg_s": state.mass_air_flow_kg_s,
            "coolant_temperature_k": state.coolant_temperature_k,
            "intake_air_temperature_k": state.intake_air_temperature_k,
            "fuel_level": state.fuel_level,
            "control_voltage_v": state.control_voltage_v,
        },
    }

    # Encoders are contract boundaries too: never emit a payload that our own
    # decoder would reject.
    from .vehicle_state_validator import validate_vehicle_state

    validate_vehicle_state(payload)
    return payload
