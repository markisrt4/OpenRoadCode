# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Toolkit-independent computing-unit performance presentation contract."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class SystemDiagnosticsSnapshot:
    """One read-only host snapshot; unavailable measurements remain None."""

    hostname: str = ""
    platform: str = ""
    sampled_at_unix_s: float | None = None

    cpu_percent: float | None = None
    per_core_percent: tuple[float, ...] = ()
    load_1m: float | None = None
    cpu_count: int | None = None
    cpu_frequency_mhz: float | None = None

    memory_used_percent: float | None = None
    memory_available_mb: float | None = None
    memory_used_mb: float | None = None
    memory_total_mb: float | None = None

    swap_used_mb: float | None = None
    swap_total_mb: float | None = None

    disk_used_percent: float | None = None
    disk_free_gb: float | None = None
    disk_total_gb: float | None = None

    temperature_c: float | None = None
    thermal_limit_c: float | None = None
    thermal_headroom_c: float | None = None
    throttled_flags: str | None = None
    uptime_seconds: float | None = None
    network_receive_bytes_per_second: float | None = None
    network_transmit_bytes_per_second: float | None = None
    disk_read_bytes_per_second: float | None = None
    disk_write_bytes_per_second: float | None = None


class SystemDiagnosticsProviderIf(Protocol):
    """Provider consumed by system-performance frontends."""

    def snapshot(self) -> SystemDiagnosticsSnapshot:
        """Return the latest system-performance snapshot."""
        ...
