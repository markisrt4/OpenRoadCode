# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Toolkit-independent computing-unit performance presentation contract."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True, slots=True)
class OrcProcessSnapshot:
    """One visible ORC process; CPU percent is in units of one logical core."""

    pid: int
    name: str
    category: str
    state: str
    cpu_percent: float | None = None
    rss_bytes: int | None = None
    pss_bytes: int | None = None
    thread_count: int | None = None
    read_bytes_per_second: float | None = None
    write_bytes_per_second: float | None = None


@dataclass(frozen=True, slots=True)
class OrcWorkloadSnapshot:
    """Visible workload totals, excluding dedicated diagnostics processes."""

    processes: tuple[OrcProcessSnapshot, ...] = ()
    visibility: str = "warming_up"
    detail: str = "Waiting for process discovery"
    process_count: int = 0
    cpu_percent: float | None = None
    cpu_capacity_percent: float | None = None
    rss_bytes: int | None = None
    pss_bytes: int | None = None
    read_bytes_per_second: float | None = None
    write_bytes_per_second: float | None = None


@dataclass(frozen=True, slots=True)
class SensorHealthSnapshot:
    """Observed telemetry health; not a claim of physical sensor self-test."""

    name: str
    topic: str
    source: str | None = None
    state: str = "not_observed"
    detail: str = "Not observed; may be disabled or unconfigured"
    last_received_age_seconds: float | None = None
    last_sample_age_seconds: float | None = None
    message_rate_hz: float | None = None
    invalid_message_count: int = 0
    stale_after_seconds: float = 5.0


@dataclass(frozen=True, slots=True)
class ServiceSocketSnapshot:
    """Observed TCP/UDP socket state and counters, without an application probe."""

    name: str
    pid: int | None = None
    protocol: str = "--"
    local_endpoint: str = "--"
    remote_endpoint: str = "--"
    state: str = "not_observed"
    detail: str = "No visible process; may be disabled, unconfigured, or restricted"
    receive_bytes_per_second: float | None = None
    transmit_bytes_per_second: float | None = None
    receive_queue_bytes: int | None = None
    transmit_queue_bytes: int | None = None
    udp_drops: int | None = None
    drops_per_second: float | None = None


@dataclass(frozen=True, slots=True)
class ThermalSourceSnapshot:
    """Raw kernel reading with source identity; not a whole-device temperature."""

    zone: str
    source_type: str
    temperature_c: float
    trip_c: float | None = None


@dataclass(frozen=True, slots=True)
class SystemDiagnosticsSnapshot:
    """One read-only host snapshot; unavailable measurements remain None."""

    hostname: str = ""
    platform: str = ""
    sampled_at_unix_s: float | None = None

    cpu_percent: float | None = None
    cpu_unavailable_reason: str | None = None
    process_cpu_percent: float | None = None
    process_id: int | None = None
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
    disk_path: str = ""
    disk_free_gb: float | None = None
    disk_total_gb: float | None = None

    temperature_c: float | None = None
    thermal_limit_c: float | None = None
    thermal_headroom_c: float | None = None
    thermal_zone: str | None = None
    thermal_source_type: str | None = None
    thermal_detail: str = ""
    thermal_sources: tuple[ThermalSourceSnapshot, ...] = ()
    throttled_flags: str | None = None
    uptime_seconds: float | None = None
    network_receive_bytes_per_second: float | None = None
    network_transmit_bytes_per_second: float | None = None
    disk_read_bytes_per_second: float | None = None
    disk_write_bytes_per_second: float | None = None
    workload: OrcWorkloadSnapshot = field(default_factory=OrcWorkloadSnapshot)
    sensors: tuple[SensorHealthSnapshot, ...] = ()
    sensor_monitor_status: str = "not_started"
    services: tuple[ServiceSocketSnapshot, ...] = ()
    service_monitor_status: str = "not_started"


class SystemDiagnosticsProviderIf(Protocol):
    """Provider consumed by system-performance frontends."""

    def snapshot(self) -> SystemDiagnosticsSnapshot:
        """Return the latest system-performance snapshot."""
        ...
