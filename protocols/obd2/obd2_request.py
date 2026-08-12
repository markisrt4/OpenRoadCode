# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Obd2Request:
    """A SAE J1979 diagnostic-service request.

    ``mode`` is the request service/mode byte, such as ``0x01`` for current
    powertrain data. ``pid`` is optional because not every diagnostic service
    uses a one-byte PID.
    """

    mode: int
    pid: int | None = None

    def __post_init__(self) -> None:
        if not 0 <= self.mode <= 0xFF:
            raise ValueError("mode must be in range 0x00..0xFF")
        if self.pid is not None and not 0 <= self.pid <= 0xFF:
            raise ValueError("pid must be in range 0x00..0xFF")
