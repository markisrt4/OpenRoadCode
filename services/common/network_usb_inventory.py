# SPDX-License-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Read-only, bounded network and USB inventory for Linux and Termux runtimes."""

from __future__ import annotations

import socket
import os
import json
from urllib.request import urlopen
import time
from pathlib import Path


def _read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8").strip()[:256]
    except (OSError, UnicodeError):
        return None


def _android_bridge_inventory() -> dict | None:
    """Termux can ask the loopback-only Companion for Android-owned interfaces."""
    try:
        with urlopen("http://127.0.0.1:18766/network/diagnostics", timeout=0.4) as response:
            if response.status != 200:
                return None
            raw = response.read(262145)
        if len(raw) > 262144:
            return None
        report = json.loads(raw)
        if not isinstance(report, dict) or not isinstance(report.get("networks"), list):
            return None
        return report
    except (OSError, ValueError, TimeoutError):
        return None


def collect_inventory(*, sys_root: Path = Path("/sys")) -> dict:
    """No subprocesses, device opens, permission changes, or active probing."""
    networks = []
    net_root = sys_root / "class/net"
    try:
        interfaces = sorted(net_root.iterdir(), key=lambda path: path.name)[:128]
        net_status = "available"
    except OSError:
        interfaces = []
        net_status = "restricted_or_unavailable"
    if not interfaces and sys_root == Path("/sys"):
        # Android/Termux may block /sys/class/net even while interfaces exist.
        try:
            names = [name for _, name in socket.if_nameindex() if name != "lo"][:128]
        except OSError:
            names = []
        if not names:
            raw = _read(Path("/proc/net/dev"))
            if raw:
                names = [line.split(":", 1)[0].strip() for line in raw.splitlines()
                         if ":" in line and line.split(":", 1)[0].strip() != "lo"][:128]
        if names:
            interfaces = [net_root / name for name in names]
            net_status = "partial_android_restricted"
    for interface in interfaces:
        if interface.name == "lo":
            continue
        networks.append({
            "interface": interface.name,
            "state": _read(interface / "operstate"),
            "mac": _read(interface / "address"),
            "speed_mbps": _read(interface / "speed"),
            "mtu": _read(interface / "mtu"),
            "rx_bytes": _read(interface / "statistics/rx_bytes"),
            "tx_bytes": _read(interface / "statistics/tx_bytes"),
            "usb_backing": "unconfirmed",
        })
    devices = []
    usb_root = sys_root / "bus/usb/devices"
    try:
        usb_entries = sorted(usb_root.iterdir(), key=lambda path: path.name)[:256]
        usb_status = "available"
    except OSError:
        usb_entries = []
        usb_status = "restricted_or_unavailable"
    readable = 0
    for entry in usb_entries:
        vid = _read(entry / "idVendor")
        pid = _read(entry / "idProduct")
        if not vid or not pid:
            continue
        readable += 1
        devices.append({
            "sysfs_name": entry.name,
            "vendor_id_hex": vid,
            "product_id_hex": pid,
            "manufacturer": _read(entry / "manufacturer"),
            "product": _read(entry / "product"),
            "speed": _read(entry / "speed"),
            "bMaxPower": _read(entry / "bMaxPower"),
            "detection": "confirmed_usb_sysfs",
        })
    if usb_entries and not readable:
        usb_status = "empty_or_restricted"
    android = None
    if sys_root == Path("/sys") and os.environ.get("PREFIX", "").startswith("/data/data/com.termux/"):
        android = _android_bridge_inventory()
    if android is not None:
        # Android ConnectivityManager and UsbManager can see devices hidden from Termux.
        return {
            "timestamp_ms": int(time.time() * 1000),
            "source": "android_companion_via_termux",
            "networks_status": "android_api",
            "networks": android.get("networks", [])[:128],
            "usb_sysfs": android.get("usb_sysfs", {"status": "unavailable", "devices": []}),
            "usb_devices": android.get("usb_devices", [])[:128],
            "system_managed_networks": android.get("system_managed_networks", [])[:128],
        }
    return {
        "timestamp_ms": int(time.time() * 1000),
        "source": "termux_restricted" if os.environ.get("PREFIX", "").startswith("/data/data/com.termux/") else "orc_runtime",
        "networks_status": net_status,
        "networks": networks,
        "usb_sysfs": {"status": usb_status, "devices": devices},
        "usb_devices": [],
        "system_managed_networks": [],
    }
