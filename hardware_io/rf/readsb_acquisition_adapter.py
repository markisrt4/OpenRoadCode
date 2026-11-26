# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Adapt an explicitly managed readsb service to RF acquisition."""

from typing import Protocol

from hardware_io.rf.receiver_discovery_if import ReceiverDevice


class ReadsbServiceIf(Protocol):
    """Privileged service operations supplied by the deployment layer."""

    def start(self, serial: str) -> bool:
        """Return true only after the selected receiver is acquired."""
        ...

    def stop(self) -> bool:
        """Return true only after all service processes have exited."""
        ...


class ReadsbAcquisitionAdapter:
    """Coordinate readsb without embedding privilege escalation."""

    def __init__(self, service: ReadsbServiceIf) -> None:
        self._service = service

    def start(self, device: ReceiverDevice) -> bool:
        """Acquire the explicitly assigned receiver."""
        if device.identity is None:
            return False
        return self._service.start(device.serial)

    def stop(self) -> bool:
        """Require the service to confirm release."""
        return self._service.stop()
