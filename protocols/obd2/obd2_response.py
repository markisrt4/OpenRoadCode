# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Obd2Response:
    """A normalized response returned by one vehicle ECU.

    ``mode`` is the response service byte received from the vehicle. For a
    positive response to a classic SAE J1979 request, this is normally the
    request mode plus ``0x40`` (for example, ``0x41`` answers mode ``0x01``).

    ``data`` contains only PID payload bytes. Transport framing, byte counts,
    echoed commands, and adapter prompt characters must be removed by the
    concrete adapter.
    """

    mode: int
    pid: int | None
    data: bytes
    ecu_id: int | None = None

    def __post_init__(self) -> None:
        if not 0 <= self.mode <= 0xFF:
            raise ValueError("mode must be in range 0x00..0xFF")
        if self.pid is not None and not 0 <= self.pid <= 0xFF:
            raise ValueError("pid must be in range 0x00..0xFF")
        if not isinstance(self.data, bytes):
            raise TypeError("data must be bytes")
        if self.ecu_id is not None and self.ecu_id < 0:
            raise ValueError("ecu_id must be non-negative")
