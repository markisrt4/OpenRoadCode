# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Acquisition lifecycle contract for coordinated RF consumers."""

from typing import Protocol

from hardware_io.rf.receiver_discovery_if import ReceiverDevice


class ReceiverAcquisitionIf(Protocol):
    def start(self, device: ReceiverDevice) -> bool:
        """Return true only when acquisition is confirmed active."""
        ...

    def stop(self) -> bool:
        """Return true only when hardware release is confirmed."""
        ...
