# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Read-only Linux host and process diagnostics sampling."""

from __future__ import annotations

import os
import platform
import shutil
import socket
import sys
from pathlib import Path

from ui.system_diagnostics import SystemDiagnosticsSnapshot


_MIB = 1024.0 * 1024.0
_GIB = 1024.0 * 1024.0 * 1024.0


class SystemDiagnosticsController:
    """Collect lightweight diagnostics without external dependencies."""

    def __init__(
        self,
        *,
        proc_root: Path | str = Path("/proc"),
        sys_root: Path | str = Path("/sys"),
        disk_path: Path | str = Path("/"),
    ) -> None:
        self._proc_root = Path(proc_root)
        self._sys_root = Path(sys_root)
        self._disk_path = Path(disk_path)
        self._previous_cpu: tuple[int, int] | None = None

    def snapshot(self) -> SystemDiagnosticsSnapshot:
        cpu_percent = self._read_cpu_percent()
        load_1m = self._read_load_1m()
        cpu_count = os.cpu_count()

        memory_total, memory_available = self._read_memory()
        memory_used = None
        memory_used_percent = None
        if memory_total is not None and memory_available is not None and memory_total > 0:
            memory_used = memory_total - memory_available
            memory_used_percent = 100.0 * memory_used / memory_total

        disk_total, disk_free = self._read_disk()
        disk_used_percent = None
        if disk_total is not None and disk_free is not None and disk_total > 0:
            disk_used_percent = 100.0 * (disk_total - disk_free) / disk_total

        temperature_c = self._read_temperature_c()
        uptime_seconds = self._read_uptime_seconds()
        process_rss_mb, process_threads = self._read_process_status()

        warnings = self._warnings(
            cpu_percent=cpu_percent,
            load_1m=load_1m,
            cpu_count=cpu_count,
            memory_used_percent=memory_used_percent,
            disk_used_percent=disk_used_percent,
            temperature_c=temperature_c,
        )

        return SystemDiagnosticsSnapshot(
            cpu_percent=cpu_percent,
            load_1m=load_1m,
            cpu_count=cpu_count,
            memory_used_percent=memory_used_percent,
            memory_used_mb=None if memory_used is None else memory_used / _MIB,
            memory_total_mb=None if memory_total is None else memory_total / _MIB,
            disk_used_percent=disk_used_percent,
            disk_free_gb=None if disk_free is None else disk_free / _GIB,
            disk_total_gb=None if disk_total is None else disk_total / _GIB,
            temperature_c=temperature_c,
            uptime_seconds=uptime_seconds,
            process_rss_mb=process_rss_mb,
            process_threads=process_threads,
            hostname=socket.gethostname(),
            platform_name=platform.platform(aliased=True, terse=True),
            kernel_release=platform.release(),
            python_version=platform.python_version(),
            warnings=warnings,
        )

    def _read_cpu_percent(self) -> float | None:
        try:
            line = (self._proc_root / "stat").read_text(encoding="utf-8").splitlines()[0]
            fields = [int(value) for value in line.split()[1:]]
            if len(fields) < 4:
                return None
            idle = fields[3] + (fields[4] if len(fields) > 4 else 0)
            total = sum(fields)
        except (OSError, ValueError, IndexError):
            return None

        current = (total, idle)
        previous = self._previous_cpu
        self._previous_cpu = current
        if previous is None:
            return None

        total_delta = total - previous[0]
        idle_delta = idle - previous[1]
        if total_delta <= 0:
            return None
        value = 100.0 * (1.0 - idle_delta / total_delta)
        return max(0.0, min(100.0, value))

    @staticmethod
    def _read_load_1m() -> float | None:
        try:
            return os.getloadavg()[0]
        except (AttributeError, OSError):
            return None

    def _read_memory(self) -> tuple[int | None, int | None]:
        values: dict[str, int] = {}
        try:
            for line in (self._proc_root / "meminfo").read_text(encoding="utf-8").splitlines():
                key, _, remainder = line.partition(":")
                if key not in {"MemTotal", "MemAvailable"}:
                    continue
                values[key] = int(remainder.strip().split()[0]) * 1024
        except (OSError, ValueError, IndexError):
            return None, None
        return values.get("MemTotal"), values.get("MemAvailable")

    def _read_disk(self) -> tuple[int | None, int | None]:
        try:
            usage = shutil.disk_usage(self._disk_path)
        except OSError:
            return None, None
        return usage.total, usage.free

    def _read_temperature_c(self) -> float | None:
        temperatures: list[float] = []
        thermal_root = self._sys_root / "class" / "thermal"
        try:
            temperature_files = thermal_root.glob("thermal_zone*/temp")
            for path in temperature_files:
                try:
                    value = float(path.read_text(encoding="utf-8").strip())
                except (OSError, ValueError):
                    continue
                if value > 1000.0:
                    value /= 1000.0
                if 0.0 <= value <= 150.0:
                    temperatures.append(value)
        except OSError:
            return None
        return max(temperatures) if temperatures else None

    def _read_uptime_seconds(self) -> float | None:
        try:
            return float((self._proc_root / "uptime").read_text(encoding="utf-8").split()[0])
        except (OSError, ValueError, IndexError):
            return None

    def _read_process_status(self) -> tuple[float | None, int | None]:
        rss_mb: float | None = None
        threads: int | None = None
        try:
            lines = (self._proc_root / "self" / "status").read_text(encoding="utf-8").splitlines()
        except OSError:
            return rss_mb, threads

        for line in lines:
            if line.startswith("VmRSS:"):
                try:
                    rss_mb = int(line.split()[1]) / 1024.0
                except (ValueError, IndexError):
                    pass
            elif line.startswith("Threads:"):
                try:
                    threads = int(line.split()[1])
                except (ValueError, IndexError):
                    pass
        return rss_mb, threads

    @staticmethod
    def _warnings(
        *,
        cpu_percent: float | None,
        load_1m: float | None,
        cpu_count: int | None,
        memory_used_percent: float | None,
        disk_used_percent: float | None,
        temperature_c: float | None,
    ) -> tuple[str, ...]:
        warnings: list[str] = []
        if temperature_c is not None and temperature_c >= 80.0:
            warnings.append(f"High CPU temperature: {temperature_c:.0f}°C")
        if memory_used_percent is not None and memory_used_percent >= 90.0:
            warnings.append(f"High memory use: {memory_used_percent:.0f}%")
        if disk_used_percent is not None and disk_used_percent >= 90.0:
            warnings.append(f"Low root filesystem free space: {100.0 - disk_used_percent:.0f}% free")
        if cpu_percent is not None and cpu_percent >= 95.0:
            warnings.append(f"CPU saturation: {cpu_percent:.0f}%")
        if load_1m is not None and cpu_count and load_1m >= cpu_count * 1.5:
            warnings.append(f"High system load: {load_1m:.1f} on {cpu_count} CPUs")
        return tuple(warnings)
