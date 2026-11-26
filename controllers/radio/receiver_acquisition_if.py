# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Acquisition lifecycle contract for coordinated RF consumers."""

from typing import Protocol

from hardware_io.rf.receiver_discovery_if import ReceiverDevice


class ReceiverAcquisitionIf(Protocol):
    def start(self, device: ReceiverDevice) -> bool:
        """!
        @brief Request acquisition of the assigned receiver.
        @param device Discovered receiver with a persistent identity.
        @return True only when acquisition is confirmed active.
        """
        ...

    def stop(self) -> bool:
        """!
        @brief Request release of the acquired receiver.
        @return True only when hardware release is confirmed.
        """
        ...
