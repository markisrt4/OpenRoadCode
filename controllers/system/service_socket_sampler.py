# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Attribute visible TCP/UDP sockets to ORC processes without opening probes."""

from __future__ import annotations

import os
import re
import subprocess
import time
from pathlib import Path

from ui.system_diagnostics import OrcWorkloadSnapshot, ServiceSocketSnapshot
from controllers.system.service_socket_parser import parse_socket_table, parse_tcp_counters, counter_rate

# Absent optional integrations are unknown, not failed services.
KNOWN_SERVICES = {
    "messaging.zeromq.broker_cli": "Message broker",
    "services.navigation": "Navigation",
    "services.automotive": "Automotive",
    "services.android.android_sensor_service_cli": "Android sensors",
    "services.trip": "Trip",
    "services.weather": "Weather",
    "services.common.service_manager_http": "Service manager",
    "services.linux.systemd_service_manager_http": "Service manager",
    "services.termux.service_manager_http": "Service manager",
    "ADS-B integration": "ADS-B",
    "GPSD integration": "GPSD",
    "SDR++ integration": "SDR++",
    "Map renderer": "Map renderer",
}


class ServiceSocketSampler:
    """Use procfs ownership plus optional kernel TCP_INFO; UDP rates stay unknown."""

    def __init__(self, proc_root: Path | str = "/proc", *, monotonic=time.monotonic,
                 tcp_reader=None, max_rows: int = 256) -> None:
        if max_rows <= 0:
            raise ValueError("Service socket row limit must be positive")
        self._root = Path(proc_root)
        self._clock = monotonic
        self._tcp_reader = tcp_reader or _tcp_counters
        self._max_rows = max_rows
        self._previous = {}
        self.status = "not_started"

    def sample(self, workload: OrcWorkloadSnapshot) -> tuple[ServiceSocketSnapshot, ...]:
        """Report visible endpoints, distinguishing observation from application health."""
        now = self._clock()
        previous, self._previous = self._previous, {}
        warnings = []
        try:
            counters = parse_tcp_counters(self._tcp_reader())
        except (OSError, subprocess.SubprocessError):
            counters = {}
            warnings.append("TCP byte counters unavailable; install iproute2/ss and check OS permissions")
        try:
            own_namespace = os.readlink(self._root / "self/ns/net")
        except OSError:
            own_namespace = None
        tables = {}
        observed_names = set()
        rows = []
        for process in workload.processes:
            name = next((label for prefix, label in KNOWN_SERVICES.items() if process.name.startswith(prefix)), process.name)
            observed_names.add(name)
            directory = self._root / str(process.pid)
            inaccessible = False
            inodes = set()
            try:
                namespace = os.readlink(directory / "ns/net")
                for fd in (directory / "fd").iterdir():
                    try:
                        link = os.readlink(fd)
                        match = re.fullmatch(r"socket:\[(\d+)\]", link)
                        if match:
                            inodes.add(int(match[1]))
                    except FileNotFoundError:
                        continue  # Descriptor or process exited during discovery.
            except OSError:
                inaccessible = True
                namespace = f"unknown:{process.pid}"
            if namespace not in tables:
                records = []
                denied = False
                for filename, protocol in (("tcp", "TCP"), ("tcp6", "TCP"), ("udp", "UDP"), ("udp6", "UDP")):
                    try:
                        records.extend(parse_socket_table((directory / "net" / filename).read_text(), protocol))
                    except OSError:
                        denied = True
                tables[namespace] = (records, denied)
            records, denied = tables[namespace]
            inaccessible = inaccessible or denied
            if inaccessible:
                warnings.append("Socket visibility restricted or process exited during discovery")
            owned = [record for record in records if record.inode in inodes]
            if not owned:
                rows.append(ServiceSocketSnapshot(name=name, pid=process.pid,
                    state="unavailable" if inaccessible else "stopped" if process.state in {"Z", "T", "t", "X"} else "no_socket",
                    detail="Socket access restricted or process exited" if inaccessible else
                           "Visible process has no TCP/UDP sockets; may use IPC, serial, or be starting"))
            for record in owned:
                cookie, rx, tx = counters.get(record.inode, ("", None, None)) if namespace == own_namespace else ("", None, None)
                key = (namespace, record.inode, cookie, record.protocol, record.local, record.remote)
                before = previous.get(key, (now, None, None, None))
                elapsed = now - before[0]
                receive = counter_rate(rx, before[1], elapsed) if record.protocol == "TCP" else None
                transmit = counter_rate(tx, before[2], elapsed) if record.protocol == "TCP" else None
                drops = counter_rate(record.drops, before[3], elapsed)
                self._previous[key] = (now, rx, tx, record.drops)
                state = "dropping" if drops is not None and drops > 0 else record.state
                if process.state in {"Z", "T", "t", "X"}:
                    state = "stopped"
                detail = ("TCP socket state, not an application response check. Payload byte rates from kernel TCP_INFO; "
                          "-- means warmup, missing counters, or reset. Includes retransmitted payload; excludes headers."
                          if record.protocol == "TCP" else
                          "UDP socket observed, not a delivery check. OS exposes queues and drops but no per-socket byte counters; bandwidth unavailable.")
                if record.protocol == "TCP" and namespace != own_namespace:
                    detail += " TCP counters belong to another or inaccessible network namespace."
                if inaccessible:
                    detail += " Socket visibility is partial."
                rows.append(ServiceSocketSnapshot(
                    name=name, pid=process.pid, protocol=record.protocol,
                    local_endpoint=record.local, remote_endpoint=record.remote, state=state, detail=detail,
                    receive_bytes_per_second=receive, transmit_bytes_per_second=transmit,
                    receive_queue_bytes=record.rx_queue, transmit_queue_bytes=record.tx_queue,
                    udp_drops=record.drops, drops_per_second=drops,
                ))
        for name in dict.fromkeys(KNOWN_SERVICES.values()):
            if name not in observed_names:
                rows.append(ServiceSocketSnapshot(name=name))
        rows.sort(key=lambda row: (row.pid is None, row.name, row.pid or 0, row.protocol, row.local_endpoint, row.remote_endpoint))
        if len(rows) > self._max_rows:
            warnings.append(f"Showing {self._max_rows} of {len(rows)} endpoint rows")
        if workload.visibility != "visible":
            warnings.append("Process discovery is incomplete; hidden services cannot be measured")
        self.status = "; ".join(dict.fromkeys(warnings)) if warnings else "Visible ORC TCP/UDP sockets; application health is not probed"
        return tuple(rows[:self._max_rows])


def _tcp_counters() -> str:
    result = subprocess.run(["ss", "-H", "-t", "-a", "-n", "-i", "-e", "-O"],
                            capture_output=True, text=True, timeout=0.5, check=True)
    return result.stdout
