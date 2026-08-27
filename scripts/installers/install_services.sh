#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"

RUN_VNC=0
RUN_GPSD_SERVICE=0
RUN_TELEMETRY_SERVICES=0
GPS_DEVICE="${GPS_DEVICE:-/dev/ttyACM0}"

usage() {
  cat <<EOF
Usage: $0 [options]

Options:
  --vnc                Configure the VNC user service
  --gpsd               Configure the GPSD system service
  --telemetry          Configure OpenRoadCode broker/navigation/automotive services
  --gps-device DEVICE  GPS serial device (default: $GPS_DEVICE)
  -h, --help           Show this help
EOF
}

while (( $# > 0 )); do
  case "$1" in
    --vnc) RUN_VNC=1 ;;
    --gpsd) RUN_GPSD_SERVICE=1 ;;
    --telemetry) RUN_TELEMETRY_SERVICES=1 ;;
    --gps-device)
      shift
      if (( $# == 0 )); then
        echo "[!] --gps-device requires a value" >&2
        exit 1
      fi
      GPS_DEVICE="$1"
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[!] Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
  shift
done

if (( ! RUN_VNC && ! RUN_GPSD_SERVICE && ! RUN_TELEMETRY_SERVICES )); then
  echo "[*] No services selected."
  exit 0
fi

if (( RUN_VNC )); then
  echo "[*] Setting up VNC..."
  bash "$PROJECT_ROOT/scripts/installers/setup_vnc.sh"
fi

if (( RUN_GPSD_SERVICE )); then
  echo "[*] Installing GPSD systemd service for $GPS_DEVICE..."
  sudo bash "$PROJECT_ROOT/scripts/systemd/install_gpsd_systemd.sh" "$GPS_DEVICE"
fi

if (( RUN_TELEMETRY_SERVICES )); then
  echo "[*] Installing OpenRoadCode telemetry services..."
  sudo bash "$PROJECT_ROOT/scripts/systemd/install_telemetry_services_systemd.sh"
fi
