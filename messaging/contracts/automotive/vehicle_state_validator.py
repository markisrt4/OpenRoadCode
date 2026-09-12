# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Validation for the public vehicle-state wire contract."""

import math
from collections.abc import Mapping
from typing import Any

from messaging.contracts.common import validate_timestamp

from .vehicle_state_codec import SCHEMA_VERSION

TOP_LEVEL_FIELDS = {"version", "timestamp", "source", "data"}
V1_DATA_FIELDS = {
    "engine_speed_rad_s",
    "vehicle_speed_m_s",
    "transmission_gear",
    "throttle_position",
    "accelerator_pedal_position",
    "engine_load",
    "intake_manifold_pressure_pa",
    "barometric_pressure_pa",
    "boost_pressure_pa",
    "mass_air_flow_kg_s",
    "coolant_temperature_k",
    "intake_air_temperature_k",
    "fuel_level",
    "control_voltage_v",
    "fuel_rail_pressure_pa",
}
V2_DATA_FIELDS = V1_DATA_FIELDS | {"engine_fuel_rate_m3_s"}
V3_DATA_FIELDS = V2_DATA_FIELDS | {"commanded_equivalence_ratio"}
DATA_FIELDS = V3_DATA_FIELDS | {
    "commanded_throttle_position",
    "absolute_engine_load",
    "fuel_system_status_1",
    "fuel_system_status_2",
    "short_term_fuel_trim_bank1",
    "long_term_fuel_trim_bank1",
    "ignition_timing_advance_deg",
    "fuel_rail_pressure_pa",
    "measured_equivalence_ratio",
}
RATIO_FIELDS = {
    "throttle_position",
    "accelerator_pedal_position",
    "engine_load",
    "absolute_engine_load",
    "commanded_throttle_position",
    "fuel_level",
}
NONNEGATIVE_FIELDS = {
    "engine_speed_rad_s",
    "vehicle_speed_m_s",
    "intake_manifold_pressure_pa",
    "barometric_pressure_pa",
    "mass_air_flow_kg_s",
    "engine_fuel_rate_m3_s",
    "control_voltage_v",
}
TEMPERATURE_FIELDS = {"coolant_temperature_k", "intake_air_temperature_k"}
VALID_GEARS = {-1, 0, 1, 2, 3, 4, 5, 6}


def _validate_number(name: str, value: Any) -> None:
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be numeric or null")
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")


def validate_vehicle_state(payload: Mapping[str, Any]) -> None:
    """Raise ValueError unless payload exactly satisfies contract version 1."""
    if not isinstance(payload, Mapping):
        raise ValueError("vehicle state payload must be an object")
    if set(payload) != TOP_LEVEL_FIELDS:
        raise ValueError("vehicle state envelope contains missing or unknown fields")

    version = payload["version"]
    if isinstance(version, bool) or not isinstance(version, int):
        raise ValueError("vehicle state version must be an integer")
    if version not in {1, 2, 3, SCHEMA_VERSION}:
        raise ValueError(f"unsupported vehicle state version: {version}")

    timestamp = payload["timestamp"]
    if not isinstance(timestamp, Mapping):
        raise ValueError("vehicle state timestamp must be an object")
    validate_timestamp(timestamp)

    source = payload["source"]
    if not isinstance(source, str) or not source.strip():
        raise ValueError("vehicle state source must be a non-empty string")

    data = payload["data"]
    if not isinstance(data, Mapping):
        raise ValueError("vehicle state data must be an object")
    expected_fields = (
        V1_DATA_FIELDS if version == 1 else
        V2_DATA_FIELDS if version == 2 else
        V3_DATA_FIELDS if version == 3 else
        DATA_FIELDS
    )
    actual_fields = set(data)
    if actual_fields != expected_fields:
        missing = sorted(expected_fields - actual_fields)
        unknown = sorted(actual_fields - expected_fields)
        raise ValueError(
            "vehicle state data schema mismatch: "
            f"missing={missing}, unknown={unknown}"
        )

    for name in ("fuel_system_status_1", "fuel_system_status_2"):
        if name in expected_fields:
            value = data[name]
            if value is not None and (
                isinstance(value, bool)
                or not isinstance(value, int)
                or not 0 <= value <= 0xFF
            ):
                raise ValueError(f"{name} must be null or an 8-bit integer")

    gear = data["transmission_gear"]
    if gear is not None and (
        isinstance(gear, bool)
        or not isinstance(gear, int)
        or gear not in VALID_GEARS
    ):
        raise ValueError("transmission_gear must be null, -1, 0, or 1..6")

    for name in expected_fields - {
        "transmission_gear",
        "fuel_system_status_1",
        "fuel_system_status_2",
    }:
        value = data[name]
        _validate_number(name, value)
        if value is None:
            continue
        if name in RATIO_FIELDS and not 0.0 <= value <= 1.0:
            raise ValueError(f"{name} must be in range 0.0..1.0")
        if name in {"commanded_equivalence_ratio", "measured_equivalence_ratio"} and not 0.0 <= value <= 2.0:
            raise ValueError(
                "commanded_equivalence_ratio must be in range 0.0..2.0"
            )
        if name in NONNEGATIVE_FIELDS and value < 0.0:
            raise ValueError(f"{name} cannot be negative")
        if name in TEMPERATURE_FIELDS and value < 0.0:
            raise ValueError(f"{name} cannot be below absolute zero")
