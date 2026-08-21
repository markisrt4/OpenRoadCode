# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Vehicle-state-specific telemetry publication."""

from controllers.automotive.vehicle_state import VehicleState

from .publisher_if import TelemetryPublisherIf
from .topics import VEHICLE_STATE_TOPIC
from .vehicle_state_payload import vehicle_state_payload


class VehicleStatePublisher:
    """Publish normalized VehicleState snapshots on the public vehicle topic."""

    def __init__(self, publisher: TelemetryPublisherIf) -> None:
        self._publisher = publisher

    def publish(self, state: VehicleState) -> None:
        self._publisher.publish(
            VEHICLE_STATE_TOPIC,
            vehicle_state_payload(state),
        )
