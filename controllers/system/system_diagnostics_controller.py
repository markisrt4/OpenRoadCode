# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Read-only Linux computing-unit performance sampling for OpenRoadCode."""

from __future__ import annotations

import os
import platform
import shutil
import socket
import subprocess
import time
from collections.abc import Callable
from pathlib import Path

from ui.system_diagnostics import SystemDiagnosticsSnapshot, ThermalSourceSnapshot

_MIB = 1024.0 * 1024.0
_GIB = 1024.0 * 1024.0 * 1024.0


class SystemDiagnosticsController:
    """Collect lightweight host metrics without external dependencies."""

    def __init__(
        self,
        *,
        proc_root: Path | str = Path("/proc"),
        sys_root: Path | str = Path("/sys"),
        disk_path: Path | str | None = None,
        monotonic: Callable[[], float] = time.monotonic,
        process_time: Callable[[], float] = time.process_time,
    ) -> None:
        self._proc_root = Path(proc_root)
        self._sys_root = Path(sys_root)
        termux = bool(os.environ.get("TERMUX_VERSION")) or os.environ.get("PREFIX", "").startswith("/data/data/com.termux/files/usr")
        self._android = termux or platform.system() == "Android"
        self._thermal_sources = ()
        self._thermal_source_type = None
        self._thermal_detail = ""
        self._disk_path = Path(disk_path) if disk_path is not None else (Path.home() if termux else Path("/"))
        self._previous_cpu: dict[str, tuple[int, int]] = {}
        self._monotonic = monotonic
        self._process_time = process_time
        self._previous_process_cpu: tuple[float, float] | None = None
        self._cpu_unavailable_reason: str | None = "warming up"
        self._previous_io: dict[str, tuple[float, dict[str, tuple[int, int]]]] = {}

    def snapshot(self) -> SystemDiagnosticsSnapshot:
        cpu_percent, per_core_percent = self._read_cpu_percentages()
        memory = self._read_memory()

        memory_total = memory.get("MemTotal")
        memory_available = memory.get("MemAvailable")
        memory_used = None
        memory_used_percent = None
        if memory_total and memory_available is not None:
            memory_used = memory_total - memory_available
            memory_used_percent = 100.0 * memory_used / memory_total

        swap_total = memory.get("SwapTotal")
        swap_free = memory.get("SwapFree")
        swap_used = None
        if swap_total is not None and swap_free is not None:
            swap_used = swap_total - swap_free

        disk_total, disk_used, disk_free = self._read_disk()
        disk_used_percent = None
        if disk_total and disk_used is not None:
            disk_used_percent = 100.0 * disk_used / disk_total

        temperature_c, thermal_limit_c, thermal_zone = self._read_thermal_state()
        now = self._monotonic()
        process_cpu_percent = self._read_process_cpu_percent(now)
        network_rx, network_tx = self._rates("network", self._read_network(), now)
        disk_read, disk_write = self._rates("disk", self._read_disk_counters(), now)

        return SystemDiagnosticsSnapshot(
            hostname=socket.gethostname(),
            platform=platform.system() + " " + platform.machine(),
            sampled_at_unix_s=time.time(),
            cpu_percent=cpu_percent,
            cpu_unavailable_reason=self._cpu_unavailable_reason,
            process_cpu_percent=process_cpu_percent,
            process_id=os.getpid(),
            per_core_percent=per_core_percent,
            load_1m=self._read_load_1m(),
            cpu_count=os.cpu_count(),
            cpu_frequency_mhz=self._read_cpu_frequency_mhz(),
            memory_used_percent=memory_used_percent,
            memory_available_mb=None if memory_available is None else memory_available / _MIB,
            memory_used_mb=None if memory_used is None else memory_used / _MIB,
            memory_total_mb=None if memory_total is None else memory_total / _MIB,
            swap_used_mb=None if swap_used is None else swap_used / _MIB,
            swap_total_mb=None if swap_total is None else swap_total / _MIB,
            disk_used_percent=disk_used_percent,
            disk_path=str(self._disk_path),
            disk_free_gb=None if disk_free is None else disk_free / _GIB,
            disk_total_gb=None if disk_total is None else disk_total / _GIB,
            temperature_c=temperature_c,
            thermal_limit_c=thermal_limit_c,
            thermal_zone=thermal_zone,
            thermal_source_type=self._thermal_source_type, thermal_detail=self._thermal_detail,
            thermal_sources=self._thermal_sources,
            thermal_headroom_c=(
                None
                if temperature_c is None or thermal_limit_c is None
                else max(0.0, thermal_limit_c - temperature_c)
            ),
            throttled_flags=self._read_throttled_flags(),
            uptime_seconds=self._read_uptime_seconds(),
            network_receive_bytes_per_second=network_rx,
            network_transmit_bytes_per_second=network_tx,
            disk_read_bytes_per_second=disk_read,
            disk_write_bytes_per_second=disk_write,
        )

    def _read_cpu_percentages(self) -> tuple[float | None, tuple[float, ...]]:
        try:
            lines = (self._proc_root / "stat").read_text(encoding="utf-8").splitlines()
        except PermissionError:
            self._previous_cpu = {}
            self._cpu_unavailable_reason = "blocked by operating system"
            return None, ()
        except OSError:
            self._previous_cpu = {}
            self._cpu_unavailable_reason = "CPU counters unavailable"
            return None, ()

        current: dict[str, tuple[int, int]] = {}
        percentages: dict[str, float] = {}
        for line in lines:
            fields = line.split()
            if not fields or not (fields[0] == "cpu" or fields[0][3:].isdigit() and fields[0].startswith("cpu")):
                continue
            try:
                values = [int(value) for value in fields[1:]]
            except ValueError:
                continue
            if len(values) < 4:
                continue

            idle = values[3] + (values[4] if len(values) > 4 else 0)
            # guest and guest_nice are already included in user and nice.
            total = sum(values[:8])
            name = fields[0]
            current[name] = (total, idle)

            previous = self._previous_cpu.get(name)
            if previous is None:
                continue
            total_delta = total - previous[0]
            idle_delta = idle - previous[1]
            if total_delta <= 0 or idle_delta < 0 or idle_delta > total_delta:
                continue

            percentages[name] = max(
                0.0,
                min(100.0, 100.0 * (1.0 - idle_delta / total_delta)),
            )

        self._previous_cpu = current
        self._cpu_unavailable_reason = None if "cpu" in percentages else (
            "warming up or counters reset" if "cpu" in current else "CPU counters unavailable"
        )
        cores = tuple(
            percentages[name]
            for name in sorted(percentages, key=lambda name: -1 if name == "cpu" else int(name[3:]))
            if name != "cpu"
        )
        return percentages.get("cpu"), cores

    def _read_process_cpu_percent(self, now: float) -> float | None:
        cpu_seconds = self._process_time()
        previous = self._previous_process_cpu
        self._previous_process_cpu = (now, cpu_seconds)
        if previous is None or now <= previous[0] or cpu_seconds < previous[1]:
            return None
        # Like top's process accounting: 100% means one fully occupied core.
        # Include all threads, but not child processes; never substitute for host CPU.
        return 100.0 * (cpu_seconds - previous[1]) / (now - previous[0])

    def _rates(
        self, key: str, current: dict[str, tuple[int, int]] | None, now: float,
    ) -> tuple[float | None, float | None]:
        previous = self._previous_io.pop(key, None)
        if current is None:
            return None, None
        self._previous_io[key] = (now, current)
        if previous is None or now <= previous[0]:
            return None, None
        elapsed = now - previous[0]
        # Match individual devices/interfaces so resets and hotplug don't spike totals.
        deltas = [
            (value[0] - previous[1][name][0], value[1] - previous[1][name][1])
            for name, value in current.items()
            if name in previous[1]
            and value[0] >= previous[1][name][0]
            and value[1] >= previous[1][name][1]
        ]
        if not deltas and current:
            return None, None
        return sum(d[0] for d in deltas) / elapsed, sum(d[1] for d in deltas) / elapsed

    def _read_network(self) -> dict[str, tuple[int, int]] | None:
        try:
            lines = (self._proc_root / "net" / "dev").read_text(encoding="utf-8").splitlines()
        except OSError:
            return None
        counters = {}
        for line in lines:
            name, separator, raw = line.partition(":")
            if not separator or name.strip() == "lo":
                continue
            try:
                fields = raw.split()
                counters[name.strip()] = (int(fields[0]), int(fields[8]))
            except (ValueError, IndexError):
                continue
        return counters

    def _read_disk_counters(self) -> dict[str, tuple[int, int]] | None:
        try:
            lines = (self._proc_root / "diskstats").read_text(encoding="utf-8").splitlines()
        except OSError:
            return None
        counters = {}
        for line in lines:
            fields = line.split()
            if len(fields) < 10:
                continue
            name = fields[2]
            # Count whole physical disks, excluding partitions and stacked virtual devices.
            block = self._sys_root / "class" / "block" / name
            if not block.exists() or (block / "partition").exists():
                continue
            if name.startswith(("loop", "ram", "dm-", "md", "zram")):
                continue
            try:
                counters[name] = (int(fields[5]) * 512, int(fields[9]) * 512)
            except ValueError:
                continue
        return counters or None

    def _read_thermal_limit_c(self, zone: Path | None = None) -> float | None:
        limits = []
        paths = () if zone is None else zone.glob("trip_point_*_temp")
        for path in paths:
            try:
                kind = path.with_name(path.name.replace("_temp", "_type")).read_text().strip()
                value = float(path.read_text().strip()) / 1000.0
            except (OSError, ValueError):
                continue
            if kind in {"passive", "hot", "critical"} and 0 < value <= 150:
                limits.append(value)
        if limits:
            return min(limits)
        try:
            model = (self._sys_root / "firmware/devicetree/base/model").read_text()
        except OSError:
            return None
        return 85.0 if "Raspberry Pi" in model else None

    @staticmethod
    def _read_load_1m() -> float | None:
        try:
            return os.getloadavg()[0]
        except (AttributeError, OSError):
            return None

    def _read_memory(self) -> dict[str, int]:
        values: dict[str, int] = {}
        try:
            lines = (self._proc_root / "meminfo").read_text(encoding="utf-8").splitlines()
        except OSError:
            return values

        for line in lines:
            key, _, remainder = line.partition(":")
            if key not in {"MemTotal", "MemAvailable", "SwapTotal", "SwapFree"}:
                continue
            try:
                values[key] = int(remainder.strip().split()[0]) * 1024
            except (ValueError, IndexError):
                pass
        return values

    def _read_disk(self) -> tuple[int | None, int | None, int | None]:
        try:
            usage = shutil.disk_usage(self._disk_path)
        except OSError:
            return None, None, None
        return usage.total, usage.used, usage.free

    def _read_thermal_state(self) -> tuple[float | None, float | None, str | None]:
        self._thermal_sources = ()
        self._thermal_source_type = None
        self._thermal_detail = "No readable thermal sensors"
        root = self._sys_root / "class" / "thermal"
        sources = []
        for path in root.glob("thermal_zone*/temp"):
            try:
                value = float(path.read_text(encoding="utf-8").strip()) / 1000.0
            except (OSError, ValueError):
                continue
            try:
                kind = (path.parent / "type").read_text().strip()[:96]
            except OSError:
                kind = "unknown"
            if 0.0 <= value <= 150.0:
                sources.append(ThermalSourceSnapshot(path.parent.name, kind, value,
                                                     self._read_thermal_limit_c(path.parent)))
        self._thermal_sources = tuple(sorted(sources, key=lambda row: row.zone)[:128])
        candidates = sources
        if self._android:
            # Vendor virtual/policy zones and anonymous hottest readings are not
            # identified CPU temperatures. Retain them for inspection instead.
            physical = [row for row in sources if not any(word in row.source_type.lower()
                         for word in ("virtual", "vts", "policy"))]
            candidates = [row for row in physical if row.source_type.lower().startswith(
                ("cpu", "soc", "cpuss", "ap-therm", "ap_therm"))]
            if not candidates:
                candidates = [row for row in physical if row.source_type.lower().startswith(("battery", "batt"))]
            if not candidates:
                self._thermal_detail = "No identified CPU/battery sensor; inspect reported thermal sources"
                return None, None, None
        if not candidates:
            return None, None, None
        row = max(candidates, key=lambda row: row.temperature_c)
        self._thermal_source_type = row.source_type
        self._thermal_detail = "Kernel-reported sensor temperature, not whole-device temperature"
        return row.temperature_c, row.trip_c, row.zone

    def _read_cpu_frequency_mhz(self) -> float | None:
        values: list[float] = []
        root = self._sys_root / "devices" / "system" / "cpu"
        for path in root.glob("cpu[0-9]*/cpufreq/scaling_cur_freq"):
            try:
                values.append(float(path.read_text(encoding="utf-8").strip()) / 1000.0)
            except (OSError, ValueError):
                pass
        return sum(values) / len(values) if values else None

    @staticmethod
    def _read_throttled_flags() -> str | None:
        """Return Raspberry Pi firmware throttle flags when vcgencmd is available."""
        try:
            result = subprocess.run(
                ["vcgencmd", "get_throttled"],
                capture_output=True,
                text=True,
                timeout=0.25,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return None

        value = result.stdout.strip()
        if result.returncode != 0 or "=" not in value:
            return None
        return value.partition("=")[2].strip()

    def _read_uptime_seconds(self) -> float | None:
        try:
            return float((self._proc_root / "uptime").read_text(encoding="utf-8").split()[0])
        except (OSError, ValueError, IndexError):
            return None
