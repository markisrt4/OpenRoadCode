#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

GPS_DEVICE="${1:-/dev/ttyACM0}"
GPSD_PORT="${GPSD_PORT:-2947}"

if ! command -v gpsd >/dev/null 2>&1; then
    echo "gpsd is not installed."
    echo "Install it with: sudo apt install gpsd gpsd-clients python3-gps"
    exit 1
fi

if [[ ! -e "${GPS_DEVICE}" ]]; then
    echo "GPS device not found: ${GPS_DEVICE}"
    echo "Check USB pass-through to the VM and inspect: ls -l /dev/ttyACM* /dev/ttyUSB*"
    exit 1
fi

if [[ ! -r "${GPS_DEVICE}" ]]; then
    echo "GPS device is not readable: ${GPS_DEVICE}"
    echo "Add your user to the device's group, commonly: sudo usermod -aG dialout \"${USER}\""
    echo "Then log out and back in before retrying."
    exit 1
fi

if ss -ltn 2>/dev/null | grep -q ":${GPSD_PORT} "; then
    echo "TCP port ${GPSD_PORT} is already in use."
    echo "gpsd may already be running. Check with: gpspipe -w -n 5"
    exit 1
fi

echo "Starting gpsd"
echo "  device: ${GPS_DEVICE}"
echo "  listen: 127.0.0.1:${GPSD_PORT}"
echo "Press Ctrl+C to stop gpsd."
echo

exec gpsd \
    --foreground \
    --nowait \
    "${GPS_DEVICE}"
