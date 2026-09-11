# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Read-only Linux system-capacity sampling for OpenRoadCode."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from ui.system_diagnostics import ProcessResourceUsage, SystemDiagnosticsSnapshot

_MIB = 1024.0 * 1024.0
_GIB = 1024.0 * 1024.0 * 1024.0
_THERMAL_LIMIT_C = 85.0


class SystemDiagnosticsController:
    """Measure Pi headroom without coupling diagnostics to automotive data."""

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
        self._previous_cpu: dict[str, tuple[int, int]] = {}
        self._previous_process_cpu: dict[int, int] = {}
        self._clock_ticks = os.sysconf("SC_CLK_TCK")

    def snapshot(self) -> SystemDiagnosticsSnapshot:
        cpu_percent, per_core_percent = self._read_cpu_percentages()
        load_1m = self._read_load_1m()
        cpu_count = os.cpu_count()
        cpu_frequency_mhz = self._read_cpu_frequency_mhz()

        memory = self._read_memory()
        memory_total = memory.get("MemTotal")
        memory_available = memory.get("MemAvailable")
        swap_total = memory.get("SwapTotal")
        swap_free = memory.get("SwapFree")
        memory_used = None
        memory_used_percent = None
        if memory_total and memory_available is not None:
            memory_used = memory_total - memory_available
            memory_used_percent = 100.0 * memory_used / memory_total
        swap_used = None
        if swap_total is not None and swap_free is not None:
            swap_used = swap_total - swap_free

        disk_total, disk_free = self._read_disk()
        disk_used_percent = None
        if disk_total and disk_free is not None:
            disk_used_percent = 100.0 * (disk_total - disk_free) / disk_total

        temperature_c = self._read_temperature_c()
        thermal_headroom_c = (
            None if temperature_c is None else max(0.0, _THERMAL_LIMIT_C - temperature_c)
        )
        throttled_flags = self._read_throttled_flags()
        top_processes = self._read_top_processes()

        warnings = self._warnings(
            cpu_percent=cpu_percent,
            load_1m=load_1m,
            cpu_count=cpu_count,
            memory_used_percent=memory_used_percent,
            swap_used=swap_used,
            disk_used_percent=disk_used_percent,
            temperature_c=temperature_c,
            throttled_flags=throttled_flags,
        )
        capacity_status, capacity_reasons = self._capacity(
            cpu_percent=cpu_percent,
            memory_used_percent=memory_used_percent,
            thermal_headroom_c=thermal_headroom_c,
            throttled_flags=throttled_flags,
            warnings=warnings,
        )

        return SystemDiagnosticsSnapshot(
            cpu_percent=cpu_percent,
            per_core_percent=per_core_percent,
            load_1m=load_1m,
            cpu_count=cpu_count,
            cpu_frequency_mhz=cpu_frequency_mhz,
            memory_used_percent=memory_used_percent,
            memory_available_mb=None if memory_available is None else memory_available / _MIB,
            memory_used_mb=None if memory_used is None else memory_used / _MIB,
            memory_total_mb=None if memory_total is None else memory_total / _MIB,
            swap_used_mb=None if swap_used is None else swap_used / _MIB,
            swap_total_mb=None if swap_total is None else swap_total / _MIB,
            disk_used_percent=disk_used_percent,
            disk_free_gb=None if disk_free is None else disk_free / _GIB,
            disk_total_gb=None if disk_total is None else disk_total / _GIB,
            temperature_c=temperature_c,
            thermal_headroom_c=thermal_headroom_c,
            throttled_flags=throttled_flags,
            uptime_seconds=self._read_uptime_seconds(),
            top_processes=top_processes,
            capacity_status=capacity_status,
            capacity_reasons=capacity_reasons,
            warnings=warnings,
        )

    def _read_cpu_percentages(self) -> tuple[float | None, tuple[float, ...]]:
        try:
            lines = (self._proc_root / "stat").read_text(encoding="utf-8").splitlines()
        except OSError:
            return None, ()
        current: dict[str, tuple[int, int]] = {}
        percentages: dict[str, float] = {}
        for line in lines:
            fields = line.split()
            if not fields or not fields[0].startswith("cpu"):
                continue
            try:
                values = [int(value) for value in fields[1:]]
            except ValueError:
                continue
            if len(values) < 4:
                continue
            idle = values[3] + (values[4] if len(values) > 4 else 0)
            total = sum(values)
            current[fields[0]] = (total, idle)
            previous = self._previous_cpu.get(fields[0])
            if previous is not None:
                total_delta = total - previous[0]
                idle_delta = idle - previous[1]
                if total_delta > 0:
                    percentages[fields[0]] = max(
                        0.0, min(100.0, 100.0 * (1.0 - idle_delta / total_delta))
                    )
        self._previous_cpu = current
        cores = tuple(
            percentages[name]
            for name in sorted(percentages)
            if name != "cpu"
        )
        return percentages.get("cpu"), cores

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

    def _read_disk(self) -> tuple[int | None, int | None]:
        try:
            usage = shutil.disk_usage(self._disk_path)
        except OSError:
            return None, None
        return usage.total, usage.free

    def _read_temperature_c(self) -> float | None:
        temperatures: list[float] = []
        try:
            paths = (self._sys_root / "class" / "thermal").glob("thermal_zone*/temp")
            for path in paths:
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

    def _read_cpu_frequency_mhz(self) -> float | None:
        values: list[float] = []
        root = self._sys_root / "devices" / "system" / "cpu"
        for path in root.glob("cpu[0-9]*/cpufreq/scaling_cur_freq"):
            try:
                values.append(float(path.read_text(encoding="utf-8").strip()) / 1000.0)
            except (OSError, ValueError):
                pass
        return sum(values) / len(values) if values else None

    def _read_throttled_flags(self) -> str | None:
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

    def _read_top_processes(self) -> tuple[ProcessResourceUsage, ...]:
        entries: list[ProcessResourceUsage] = []
        current_ticks: dict[int, int] = {}
        total_memory = self._read_memory().get("MemTotal")
        del total_memory  # retained here only to keep process sampling procfs-only
        try:
            process_dirs = tuple(path for path in self._proc_root.iterdir() if path.name.isdigit())
        except OSError:
            return ()
        for path in process_dirs:
            pid = int(path.name)
            try:
                stat_fields = (path / "stat").read_text(encoding="utf-8").split()
                status = (path / "status").read_text(encoding="utf-8").splitlines()
                ticks = int(stat_fields[13]) + int(stat_fields[14])
                name = stat_fields[1].strip("()")
            except (OSError, ValueError, IndexError):
                continue
            current_ticks[pid] = ticks
            previous = self._previous_process_cpu.get(pid)
            cpu_percent = 0.0
            if previous is not None:
                cpu_percent = max(0.0, (ticks - previous) / self._clock_ticks * 100.0)
            rss_mb = 0.0
            for line in status:
                if line.startswith("VmRSS:"):
                    try:
                        rss_mb = int(line.split()[1]) / 1024.0
                    except (ValueError, IndexError):
                        pass
                    break
            entries.append(ProcessResourceUsage(pid, name, cpu_percent, rss_mb))
        self._previous_process_cpu = current_ticks
        entries.sort(key=lambda item: (item.cpu_percent, item.memory_mb), reverse=True)
        return tuple(entries[:6])

    @staticmethod
    def _warnings(
        *,
        cpu_percent: float | None,
        load_1m: float | None,
        cpu_count: int | None,
        memory_used_percent: float | None,
        swap_used: int | None,
        disk_used_percent: float | None,
        temperature_c: float | None,
        throttled_flags: str | None,
    ) -> tuple[str, ...]:
        warnings: list[str] = []
        if throttled_flags not in {None, "", "0x0", "0"}:
            warnings.append(f"Pi throttle/undervoltage flags: {throttled_flags}")
        if temperature_c is not None and temperature_c >= 80.0:
            warnings.append(f"High SoC temperature: {temperature_c:.0f}°C")
        if memory_used_percent is not None and memory_used_percent >= 90.0:
            warnings.append(f"High memory use: {memory_used_percent:.0f}%")
        if swap_used is not None and swap_used >= 256 * 1024 * 1024:
            warnings.append(f"Swap pressure: {swap_used / _MIB:.0f} MiB in use")
        if disk_used_percent is not None and disk_used_percent >= 90.0:
            warnings.append(f"Low root filesystem free space: {100.0 - disk_used_percent:.0f}% free")
        if cpu_percent is not None and cpu_percent >= 90.0:
            warnings.append(f"CPU saturation: {cpu_percent:.0f}%")
        if load_1m is not None and cpu_count and load_1m >= cpu_count * 1.25:
            warnings.append(f"High system load: {load_1m:.1f} on {cpu_count} CPUs")
        return tuple(warnings)

    @staticmethod
    def _capacity(
        *,
        cpu_percent: float | None,
        memory_used_percent: float | None,
        thermal_headroom_c: float | None,
        throttled_flags: str | None,
        warnings: tuple[str, ...],
    ) -> tuple[str, tuple[str, ...]]:
        reasons: list[str] = []
        if cpu_percent is not None:
            reasons.append(f"{max(0.0, 100.0 - cpu_percent):.0f}% CPU headroom")
        if memory_used_percent is not None:
            reasons.append(f"{max(0.0, 100.0 - memory_used_percent):.0f}% RAM headroom")
        if thermal_headroom_c is not None:
            reasons.append(f"{thermal_headroom_c:.0f}°C thermal headroom")
        throttled = throttled_flags not in {None, "", "0x0", "0"}
        if throttled or len(warnings) >= 2:
            return "LIMITED", tuple(reasons)
        if (
            (cpu_percent is not None and cpu_percent >= 70.0)
            or (memory_used_percent is not None and memory_used_percent >= 80.0)
            or (thermal_headroom_c is not None and thermal_headroom_c <= 10.0)
            or warnings
        ):
            return "MODERATE", tuple(reasons)
        return "HEALTHY", tuple(reasons)
