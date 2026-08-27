# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Automotive controller contracts, state, and optional implementations."""

from importlib import import_module
from typing import Any

from controllers.automotive.vehicle_state import VehicleState
from controllers.automotive.vehicle_state_source_if import VehicleStateSourceIf

__all__ = [
    "Elm327ObdAdapter",
    "Obd2Manager",
    "SimulatedVehicleStateSource",
    "VehicleState",
    "VehicleStateSourceIf",
]

_LAZY_EXPORTS = {
    "Elm327ObdAdapter": (
        "controllers.automotive.obd2.elm327_obd_adapter",
        "Elm327ObdAdapter",
    ),
    "Obd2Manager": (
        "controllers.automotive.obd2.obd2_manager",
        "Obd2Manager",
    ),
    "SimulatedVehicleStateSource": (
        "controllers.automotive.simulated_vehicle_state_source",
        "SimulatedVehicleStateSource",
    ),
}


def __getattr__(name: str) -> Any:
    """Load concrete automotive implementations only when requested."""
    target = _LAZY_EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attribute_name = target
    value = getattr(import_module(module_name), attribute_name)
    globals()[name] = value
    return value
