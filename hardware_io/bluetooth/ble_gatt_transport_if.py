# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol, runtime_checkable


class BleGattStatus(Enum):
    """Describe one BLE GATT connection without implying device semantics."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class BleGattState:
    """Immutable state for one BLE GATT transport instance."""

    status: BleGattStatus = BleGattStatus.DISCONNECTED
    address: str | None = None
    last_error: str | None = None

    @property
    def connected(self) -> bool:
        """Return whether the transport is connected.

        @return True only for the connected state.
        """
        return self.status is BleGattStatus.CONNECTED


@runtime_checkable
class BleGattTransportIf(Protocol):
    """Async, device-agnostic BLE characteristic transport."""

    def current_state(self) -> BleGattState:
        """Return this transport instance's current connection state.

        @return Immutable GATT transport state.
        """
        ...

    async def connect(self) -> None:
        """Discover and connect to the configured GATT target."""
        ...

    async def disconnect(self) -> None:
        """Disconnect only this transport's BLE client."""
        ...

    async def write(self, data: bytes) -> None:
        """Write one payload to the configured characteristic.

        @param data Raw characteristic payload.
        """
        ...
