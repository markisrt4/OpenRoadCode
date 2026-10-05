# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Discover visible ORC processes and account for their resource use via procfs."""

from __future__ import annotations

import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from ui.system_diagnostics import OrcProcessSnapshot, OrcWorkloadSnapshot


@dataclass(frozen=True)
class _Process:
    pid: int
    parent: int
    start: int
    ticks: int
    rss: int
    threads: int
    state: str
    comm: str
    args: tuple[str, ...]


class OrcProcessSampler:
    """Measure each PID independently; never include cumulative child CPU twice."""

    def __init__(
        self, proc_root: Path | str = "/proc", *,
        monotonic: Callable[[], float] = time.monotonic,
        clock_ticks: int | None = None, page_size: int | None = None,
    ) -> None:
        self._root = Path(proc_root)
        self._monotonic = monotonic
        self._ticks = clock_ticks or os.sysconf("SC_CLK_TCK")
        self._page_size = page_size or os.sysconf("SC_PAGE_SIZE")
        self._previous: dict[tuple[int, int], tuple[float, int, dict[str, int]]] = {}
        self._tracked: dict[tuple[int, int], tuple[str, str]] = {}

    def sample(self) -> OrcWorkloadSnapshot:
        """Discover roots and descendants, and aggregate only visible workload PIDs."""
        now = self._monotonic()
        processes: dict[int, _Process] = {}
        blocked = 0
        try:
            directories = tuple(self._root.iterdir())
        except OSError:
            return OrcWorkloadSnapshot(visibility="unavailable", detail="Process directory inaccessible")
        for directory in directories:
            if not directory.name.isdigit():
                continue
            try:
                raw = (directory / "stat").read_text()
                head, _, tail = raw.rpartition(")")
                fields = tail.split()
                pid = int(directory.name)
                args = tuple(arg.decode(errors="replace") for arg in (directory / "cmdline").read_bytes().split(b"\0") if arg)
                processes[pid] = _Process(
                    pid, int(fields[1]), int(fields[19]), int(fields[11]) + int(fields[12]),
                    max(0, int(fields[21])) * self._page_size, int(fields[17]), fields[0],
                    head.partition("(")[2], args,
                )
            except PermissionError:
                blocked += 1
            except (OSError, ValueError, IndexError):
                # Processes can exit at any point during discovery.
                continue

        selected: dict[int, tuple[str, str]] = {}
        for pid, process in processes.items():
            identity = (pid, process.start)
            match = _classify(process.args)
            if match is not None:
                selected[pid] = match
            elif identity in self._tracked:
                selected[pid] = self._tracked[identity]
        # Follow actual parentage rather than attributing every Python/browser process to ORC.
        while True:
            added = False
            for pid, process in processes.items():
                if pid not in selected and process.parent in selected:
                    parent_name, category = selected[process.parent]
                    selected[pid] = (f"{parent_name} / {Path(process.args[0]).name if process.args else process.comm}", category)
                    added = True
            if not added:
                break

        previous = self._previous
        self._previous = {}
        self._tracked = {}
        rows = []
        for pid, (name, category) in selected.items():
            process = processes[pid]
            identity = (pid, process.start)
            self._tracked[identity] = (name[:96], category)
            io = self._read_values(self._root / str(pid) / "io")
            memory = self._read_values(self._root / str(pid) / "smaps_rollup")
            cpu = read = write = None
            before = previous.get(identity)
            if before is not None and now > before[0]:
                elapsed = now - before[0]
                if process.ticks >= before[1]:
                    cpu = 100 * (process.ticks - before[1]) / self._ticks / elapsed
                read = _rate(io, before[2], "read_bytes", elapsed)
                write = _rate(io, before[2], "write_bytes", elapsed)
            self._previous[identity] = (now, process.ticks, io)
            rows.append(OrcProcessSnapshot(
                pid=pid, name=name[:96], category=category, state=process.state,
                cpu_percent=cpu, rss_bytes=process.rss, pss_bytes=memory.get("Pss"),
                thread_count=process.threads, read_bytes_per_second=read,
                write_bytes_per_second=write,
            ))
        rows.sort(key=lambda row: (row.cpu_percent is None, -(row.cpu_percent or 0), row.pid))
        workload = [row for row in rows if row.category != "diagnostics"]
        cpu = _sum_complete(workload, "cpu_percent")
        count = os.cpu_count()
        return OrcWorkloadSnapshot(
            processes=tuple(rows), process_count=len(workload),
            visibility="partial" if blocked else "visible",
            detail=(f"Access denied for {blocked} process entries; totals cover visible ORC workload only"
                    if blocked else "Recognized ORC roots and their descendants; diagnostics excluded from totals"),
            cpu_percent=cpu,
            cpu_capacity_percent=None if cpu is None or not count else cpu / count,
            rss_bytes=_sum_complete(workload, "rss_bytes"),
            pss_bytes=_sum_complete(workload, "pss_bytes"),
            read_bytes_per_second=_sum_complete(workload, "read_bytes_per_second"),
            write_bytes_per_second=_sum_complete(workload, "write_bytes_per_second"),
        )

    @staticmethod
    def _read_values(path: Path) -> dict[str, int]:
        try:
            lines = path.read_text().splitlines()
        except OSError:
            return {}
        values = {}
        for line in lines:
            key, _, raw = line.partition(":")
            fields = raw.split()
            try:
                values[key] = int(fields[0]) * (1024 if len(fields) > 1 and fields[1] == "kB" else 1)
            except (ValueError, IndexError):
                continue
        return values


def _classify(args: tuple[str, ...]) -> tuple[str, str] | None:
    if not args:
        return None
    executable = Path(args[0]).name
    native = {"openroadcode-map-renderer": "Map renderer", "sdrpp": "SDR++ integration", "readsb": "ADS-B integration", "gpsd": "GPSD integration"}
    if executable in native:
        return native[executable], "workload"
    if executable.startswith("python") and "-m" in args:
        position = args.index("-m") + 1
        module = args[position] if position < len(args) else ""
        diagnostics = {
            "frontends.tk.system.component_test.performance_preview",
            "services.common.service_manager_http", "services.linux.systemd_service_manager_http",
            "services.termux.service_manager_http",
        }
        if module in diagnostics:
            return module, "diagnostics"
        roots = ("apps.orcUi", "apps.carUi", "apps.carTui", "apps.automotive_dashboard",
                 "apps.map_renderer", "apps.weatherDash", "apps.webUi", "services.android",
                 "services.automotive", "services.navigation", "services.trip", "services.weather",
                 "messaging.zeromq.broker_cli")
        if any(module == root or module.startswith(root + ".") for root in roots):
            return module, "workload"
    # Support repo scripts without matching command arguments, logs, or arbitrary grep results.
    if executable.startswith("python") and len(args) > 1 and args[1].endswith(".py"):
        script = Path(args[1])
        lowered = [part.lower() for part in script.parts]
        if "openroadcode" in lowered:
            return script.name, "diagnostics" if script.name == "performance_preview.py" else "workload"
    return None


def _rate(current: dict[str, int], previous: dict[str, int], key: str, elapsed: float) -> float | None:
    if key not in current or key not in previous or current[key] < previous[key]:
        return None
    return (current[key] - previous[key]) / elapsed


def _sum_complete(rows: list[OrcProcessSnapshot], field: str) -> float | int | None:
    values = [getattr(row, field) for row in rows]
    return None if any(value is None for value in values) else sum(values)
