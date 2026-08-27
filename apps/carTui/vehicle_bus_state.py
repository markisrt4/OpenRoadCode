# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Compatibility export for the shared vehicle telemetry cache."""

from common.telemetry.vehicle_bus_state import VehicleBusState, VehicleBusSnapshot

__all__ = ["VehicleBusState", "VehicleBusSnapshot"]
