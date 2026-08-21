# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Serialization of normalized vehicle telemetry."""

from dataclasses import asdict

from controllers.automotive.vehicle_state import VehicleState


def vehicle_state_payload(state: VehicleState) -> dict[str, object]:
    """Convert a VehicleState snapshot into its public telemetry payload."""
    payload = asdict(state)
    payload["timestamp"] = state.timestamp.isoformat()
    return payload
