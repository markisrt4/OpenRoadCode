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
from controllers.system.service_socket_parser import parse_socket_table, parse_tcp_counters, parse_ss_sockets, counter_rate

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
            ss_text = self._tcp_reader()
            counters = parse_tcp_counters(ss_text)
            netlink_records = parse_ss_sockets(ss_text)
        except (OSError, subprocess.SubprocessError) as error:
            counters = {}
            netlink_records = ()
            reason = ((error.stderr or "").strip() if isinstance(error, subprocess.CalledProcessError)
                      else str(error))
            warnings.append("TCP byte counters unavailable: " + (reason[:180] or type(error).__name__))
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
            failures = []
            inodes = set()
            process_state = "stopped" if process.state in {"Z", "T", "t", "X"} else "running"
            try:
                namespace = os.readlink(directory / "ns/net")
            except OSError:
                namespace = f"unknown:{process.pid}"
                warnings.append("Network namespace unavailable; TCP rates may be unavailable")
            try:
                for fd in (directory / "fd").iterdir():
                    try:
                        link = os.readlink(fd)
                        match = re.fullmatch(r"socket:\[(\d+)\]", link)
                        if match:
                            inodes.add(int(match[1]))
                    except FileNotFoundError:
                        continue
                    except OSError as error:
                        failures.append(f"FD ownership: {error.strerror or type(error).__name__}")
                        inaccessible = True
            except OSError as error:
                failures.append(f"FD directory: {error.strerror or type(error).__name__}")
                inaccessible = True
            if namespace not in tables:
                records = []
                denied = False
                readable = 0
                table_failures = []
                for filename, protocol in (("tcp", "TCP"), ("tcp6", "TCP"), ("udp", "UDP"), ("udp6", "UDP")):
                    try:
                        records.extend(parse_socket_table((directory / "net" / filename).read_text(), protocol))
                        readable += 1
                    except FileNotFoundError:
                        continue  # An unsupported address family is not a permission failure.
                    except OSError as error:
                        table_failures.append(f"{filename}: {error.strerror or type(error).__name__}")
                        denied = True
                # Only a verified shared namespace permits using the monitor's table.
                if readable == 0 and namespace == own_namespace:
                    for filename, protocol in (("tcp", "TCP"), ("tcp6", "TCP"), ("udp", "UDP"), ("udp6", "UDP")):
                        try:
                            records.extend(parse_socket_table((self._root / "self/net" / filename).read_text(), protocol))
                            readable += 1
                        except OSError:
                            continue
                if readable == 0 and not table_failures:
                    table_failures.append("TCP/UDP tables missing")
                tables[namespace] = (records, denied or readable == 0, table_failures)
            records, denied, table_failures = tables[namespace]
            failures.extend(table_failures)
            inaccessible = inaccessible or denied
            if inaccessible:
                warnings.append("Socket visibility restricted or process exited during discovery")
            owned = [record for record in records if record.inode in inodes]
            known = {record.inode for record in owned}
            fallback_inodes = set()
            for record in netlink_records:
                if record.inode in inodes and record.inode not in known:
                    owned.append(record)
                    known.add(record.inode)
                    fallback_inodes.add(record.inode)
            if not owned:
                rows.append(ServiceSocketSnapshot(name=name, pid=process.pid, process_state=process_state,
                    state="unavailable" if inaccessible else "stopped" if process.state in {"Z", "T", "t", "X"} else "no_socket",
                    detail="Socket inspection unavailable: " + "; ".join(dict.fromkeys(failures)) + ". Android may block this even for running services." if inaccessible else
                           "Visible process has no TCP/UDP sockets; may use IPC, serial, or be starting"))
            for record in owned:
                cookie, rx, tx = counters.get(record.inode, ("", None, None)) if namespace == own_namespace or record.inode in fallback_inodes else ("", None, None)
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
                if record.protocol == "TCP" and namespace != own_namespace and record.inode not in fallback_inodes:
                    detail += " TCP counters belong to another or inaccessible network namespace."
                if record.inode in fallback_inodes:
                    detail += " Endpoint recovered via ss/netlink and matched to owned socket inode."
                if inaccessible:
                    detail += " Socket visibility is partial: " + "; ".join(dict.fromkeys(failures)) + "."
                rows.append(ServiceSocketSnapshot(
                    name=name, pid=process.pid, process_state=process_state, protocol=record.protocol,
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
    result = subprocess.run(["ss", "-H", "-t", "-u", "-a", "-n", "-i", "-e", "-O"],
                            capture_output=True, text=True, timeout=0.5, check=True)
    return result.stdout
