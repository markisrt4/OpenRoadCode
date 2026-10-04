# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Parse Linux socket tables and optional TCP_INFO counters from iproute2."""

from __future__ import annotations

import ipaddress
import re
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class SocketRecord:
    inode: int
    protocol: str
    local: str
    remote: str
    state: str
    rx_queue: int
    tx_queue: int
    drops: int | None


TCP_STATES = {
    "01": "connected", "02": "connecting", "03": "connecting", "04": "closing",
    "05": "closing", "06": "closing", "07": "closed", "08": "closing",
    "09": "closing", "0A": "listening", "0B": "closing", "0C": "connecting",
}


def parse_socket_table(text: str, protocol: str) -> tuple[SocketRecord, ...]:
    """Read queues as occupancy, never mistake them for traffic counters."""
    rows = []
    for line in text.splitlines()[1:]:
        fields = line.split()
        try:
            tx, rx = (int(value, 16) for value in fields[4].split(":"))
            inode = int(fields[9])
            if not inode:
                continue
            rows.append(SocketRecord(
                inode, protocol, _endpoint(fields[1]), _endpoint(fields[2]),
                TCP_STATES.get(fields[3], "unknown") if protocol == "TCP" else "bound",
                rx, tx, int(fields[-1]) if protocol == "UDP" and len(fields) >= 13 else None,
            ))
        except (ValueError, IndexError):
            continue
    return tuple(rows)


def parse_tcp_counters(text: str) -> dict[int, tuple[str, int | None, int | None]]:
    """Extract socket cookie plus cumulative TCP payload received/sent bytes."""
    counters = {}
    for line in text.splitlines():
        inode = re.search(r"\bino:(\d+)\b", line)
        if inode is None:
            continue
        cookie = re.search(r"\bsk:([0-9a-fA-F]+)\b", line)
        rx = re.search(r"\bbytes_received:(\d+)\b", line)
        tx = re.search(r"\bbytes_sent:(\d+)\b", line)
        counters[int(inode[1])] = (cookie[1] if cookie else "", int(rx[1]) if rx else None,
                                   int(tx[1]) if tx else None)
    return counters


def counter_rate(current: int | None, previous: int | None, elapsed: float) -> float | None:
    """Leave first samples, resets, and missing counters unavailable."""
    if current is None or previous is None or elapsed <= 0 or current < previous:
        return None
    return (current - previous) / elapsed


def _endpoint(raw: str) -> str:
    address, port = raw.split(":")
    data = b"".join(int(address[index:index + 8], 16).to_bytes(4, sys.byteorder)
                    for index in range(0, len(address), 8))
    ip = ipaddress.ip_address(data)
    return f"[{ip}]:{int(port, 16)}" if ip.version == 6 else f"{ip}:{int(port, 16)}"
