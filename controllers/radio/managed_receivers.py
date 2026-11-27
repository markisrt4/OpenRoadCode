# SPDX-License-Identifier: MIT
"""Resolve live assignments and coordinate supervised RF acquisition."""

from __future__ import annotations

from controllers.radio.receiver_acquisition import ReceiverAcquisitionController
from controllers.radio.receiver_acquisition_if import ReceiverAcquisitionIf
from controllers.radio.receiver_assignments import ReceiverAssignmentStore
from hardware_io.rf.receiver_discovery_if import ReceiverDevice, ReceiverDiscoveryIf


class ManagedReceivers:
    """Coordinate leases for the application's RF consumers."""

    def __init__(
        self,
        coordinator: ReceiverAcquisitionController,
        assignments: ReceiverAssignmentStore,
        discovery: ReceiverDiscoveryIf,
    ) -> None:
        self._coordinator = coordinator
        self._assignments = assignments
        self._discovery = discovery

    def assignment(self, consumer: str) -> ReceiverDevice:
        assignments = self._assignments.load()
        identity = {
            "radio": assignments.radio,
            "weather": assignments.weather,
            "adsb": assignments.adsb,
        }[consumer]
        devices = self._discovery.discover()
        if identity is None:
            raise RuntimeError(f"Assign a USB receiver to {consumer} in RF Settings")
        matches = [device for device in devices if device.identity == identity]
        if not matches:
            raise RuntimeError(f"Assigned {consumer} receiver {identity} is disconnected")
        if len(matches) != 1 or sum(item.serial == matches[0].serial for item in devices) != 1:
            raise RuntimeError(f"Assigned {consumer} receiver {identity} is ambiguous")
        return matches[0]

    def start(self, consumer: str, device: ReceiverDevice, adapter: ReceiverAcquisitionIf) -> None:
        if not self._coordinator.start(consumer, device, adapter):
            raise RuntimeError(
                f"{consumer} could not acquire receiver {device.serial}. "
                "Check whether another RF consumer owns it."
            )

    def stop(self, consumer: str) -> None:
        if not self._coordinator.stop(consumer):
            raise RuntimeError(f"Release of the {consumer} receiver could not be confirmed")
