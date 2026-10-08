#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

GPS_DEVICE="${1:-/dev/ttyACM0}"
GPSD_DEFAULTS="/etc/default/gpsd"
LEGACY_SERVICE="/etc/systemd/system/gpsd-start.service"

if [[ $EUID -ne 0 ]]; then
    echo "This script needs root privileges." >&2
    echo "Please run: sudo $0 $GPS_DEVICE" >&2
    exit 1
fi

if ! command -v gpsd >/dev/null 2>&1; then
    echo "gpsd is not installed." >&2
    exit 1
fi

if ! systemctl list-unit-files gpsd.socket >/dev/null 2>&1; then
    echo "gpsd.socket is unavailable; the distro gpsd systemd units are required." >&2
    exit 1
fi

if [[ ! -e "$GPS_DEVICE" ]]; then
    echo "[!] GPS device is not currently present: $GPS_DEVICE"
    echo "    Configuration will still be installed; gpsd can use it when the device appears."
fi

python3 - "$GPSD_DEFAULTS" "$GPS_DEVICE" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
device = sys.argv[2]

values = {
    "START_DAEMON": '"true"',
    "USBAUTO": '"false"',
    "DEVICES": f'"{device}"',
    "GPSD_OPTIONS": '"-n"',
}

lines = path.read_text().splitlines() if path.exists() else []
seen = set()
output = []

for line in lines:
    stripped = line.strip()
    replaced = False
    for key, value in values.items():
        if stripped.startswith(f"{key}="):
            output.append(f"{key}={value}")
            seen.add(key)
            replaced = True
            break
    if not replaced:
        output.append(line)

for key, value in values.items():
    if key not in seen:
        output.append(f"{key}={value}")

path.write_text("\n".join(output).rstrip() + "\n")
PY

# Clean up the old OpenRoadCode-specific gpsd service if it was installed.
if systemctl list-unit-files gpsd-start.service >/dev/null 2>&1 || [[ -f "$LEGACY_SERVICE" ]]; then
    systemctl disable --now gpsd-start.service >/dev/null 2>&1 || true
    rm -f "$LEGACY_SERVICE"
fi

systemctl daemon-reload
systemctl enable gpsd.socket
systemctl restart gpsd.socket

# Restart an already-running gpsd so the updated device configuration is used.
if systemctl is-active --quiet gpsd.service; then
    systemctl restart gpsd.service
fi

echo "[+] Configured distro gpsd for OpenRoadCode"
echo "    device: $GPS_DEVICE"
echo "    socket: gpsd.socket"
echo "    verify: gpspipe -w -n 5"
