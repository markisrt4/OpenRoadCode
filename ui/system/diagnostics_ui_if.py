# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""! @brief UI contract and values for host system diagnostics."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class SystemDiagnostics:
    """! @brief Describe a snapshot of host system health.

    ``None`` indicates that a metric is unavailable. The values describe host
    state without prescribing how frequently they are collected or presented.

    @param cpu_usage_percent Total CPU usage from 0 through 100.
    @param cpu_temperature_celsius CPU temperature in degrees Celsius.
    @param memory_used_bytes Amount of physical memory currently in use.
    @param memory_total_bytes Total physical memory available to the host.
    @param disk_usage_percent Usage of the application's primary disk, from 0
        through 100.
    @param uptime_seconds Time elapsed since the host booted, in seconds.
    @param network_connected Whether the host has network connectivity.
    @param healthy_service_count Number of monitored services that are healthy.
    @param total_service_count Total number of monitored services.
    """

    cpu_usage_percent: float | None = None
    cpu_temperature_celsius: float | None = None
    memory_used_bytes: int | None = None
    memory_total_bytes: int | None = None
    disk_usage_percent: float | None = None
    uptime_seconds: float | None = None
    network_connected: bool | None = None
    healthy_service_count: int | None = None
    total_service_count: int | None = None


class SystemDiagnosticsUiIf(ABC):
    """! @brief Display a snapshot of host system diagnostics."""

    @abstractmethod
    def set_diagnostics(self, diagnostics: SystemDiagnostics | None) -> None:
        """! @brief Set or clear the current host diagnostics.

        @param diagnostics Diagnostics to display, or None to clear them.
        """
        ...
