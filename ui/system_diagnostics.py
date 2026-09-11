# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Toolkit-independent system diagnostics presentation contract."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class SystemDiagnosticsSnapshot:
    """One read-only snapshot of host and OpenRoadCode process health."""

    cpu_percent: float | None = None
    load_1m: float | None = None
    cpu_count: int | None = None

    memory_used_percent: float | None = None
    memory_used_mb: float | None = None
    memory_total_mb: float | None = None

    disk_used_percent: float | None = None
    disk_free_gb: float | None = None
    disk_total_gb: float | None = None

    temperature_c: float | None = None
    uptime_seconds: float | None = None

    process_rss_mb: float | None = None
    process_threads: int | None = None

    hostname: str = ""
    platform_name: str = ""
    kernel_release: str = ""
    python_version: str = ""

    warnings: tuple[str, ...] = ()


class SystemDiagnosticsProviderIf(Protocol):
    """Provider consumed by diagnostics frontends."""

    def snapshot(self) -> SystemDiagnosticsSnapshot:
        """Return the latest system diagnostics snapshot."""
        ...
