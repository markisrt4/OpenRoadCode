#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"

RUN_RADIO=0
MANAGED_RF=0
RUN_NAVIGATION=0
RUN_VNC=0
RUN_GPSD_SERVICE=0
RUN_TELEMETRY_SERVICES=0
RUN_SERVICE_MANAGER=0
GPS_DEVICE="${GPS_DEVICE:-/dev/ttyACM0}"

usage() {
  cat <<EOF
Usage: $0 [options]

Options:
  --navigation         Configure broker and navigation services
  --radio              Configure broker and SDRForge user service
  --managed-rf         Provision coordinated SDRForge and readsb user units
  --vnc                Configure the VNC user service
  --gpsd               Configure the GPSD system service
  --telemetry          Configure OpenRoadCode broker/navigation/automotive services
  --service-manager    Configure Android browser pairing and restricted service controls
  --gps-device DEVICE  GPS serial device (default: $GPS_DEVICE)
  -h, --help           Show this help
EOF
}

while (( $# > 0 )); do
  case "$1" in
    --navigation) RUN_NAVIGATION=1 ;;
    --radio) RUN_RADIO=1 ;;
    --managed-rf) MANAGED_RF=1 ;;
    --vnc) RUN_VNC=1 ;;
    --gpsd) RUN_GPSD_SERVICE=1 ;;
    --telemetry) RUN_TELEMETRY_SERVICES=1 ;;
    --service-manager) RUN_SERVICE_MANAGER=1 ;;
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

if (( ! RUN_VNC && ! RUN_GPSD_SERVICE && ! RUN_TELEMETRY_SERVICES && ! RUN_RADIO && ! RUN_NAVIGATION && ! RUN_SERVICE_MANAGER )); then
  echo "[*] No services selected."
  exit 0
fi

if (( RUN_SERVICE_MANAGER )); then
  echo "[*] Installing OpenRoadCode service manager for Android pairing..."
  sudo env OPENROADCODE_SERVICE_MANAGER_INSTALL_ROOT=/opt/openroadcode/service-manager-runtime \
    bash "$PROJECT_ROOT/scripts/systemd/install_service_manager_systemd.sh"
fi

if (( RUN_VNC )); then
  echo "[*] Setting up VNC..."
  bash "$PROJECT_ROOT/scripts/installers/setup_vnc.sh"
fi

if (( RUN_GPSD_SERVICE )); then
  echo "[*] Installing GPSD systemd service for $GPS_DEVICE..."
  sudo bash "$PROJECT_ROOT/scripts/systemd/install_gpsd_systemd.sh" "$GPS_DEVICE"
fi

if (( RUN_TELEMETRY_SERVICES || RUN_RADIO || RUN_NAVIGATION )); then
  if (( RUN_TELEMETRY_SERVICES )); then
    echo "[*] Installing OpenRoadCode telemetry services..."
  else
    echo "[*] Installing OpenRoadCode message broker and native radio service..."
  fi
  runtime_config="$PROJECT_ROOT/config/runtime.toml"
  python_bin="${OPENROADCODE_PYTHON:-${VENV_DIR:-$PROJECT_ROOT/venv}/bin/python}"
  if [[ ! -x "$python_bin" ]]; then
    echo "[!] OpenRoadCode service Python is missing or not executable: $python_bin" >&2
    echo "    Run the Python environment installer before installing telemetry services." >&2
    exit 1
  fi
  if [[ "${OPENROAD_INSTALL_TARGET:-}" == "linux-dev" ]]; then
    runtime_config="$PROJECT_ROOT/config/runtime.simulated.toml"
    echo "[*] linux-dev target: using simulated telemetry runtime: $runtime_config"
  fi
  installer=install_message_broker_systemd.sh
  if (( RUN_TELEMETRY_SERVICES )); then installer=install_telemetry_services_systemd.sh; fi
  sudo env \
    OPENROADCODE_RUNTIME_CONFIG="$runtime_config" \
    OPENROADCODE_PYTHON="$python_bin" \
    bash "$PROJECT_ROOT/scripts/systemd/$installer"
  if (( RUN_NAVIGATION && ! RUN_TELEMETRY_SERVICES )); then
    sudo env OPENROADCODE_RUNTIME_CONFIG="$runtime_config" OPENROADCODE_PYTHON="$python_bin" bash "$PROJECT_ROOT/scripts/systemd/install_navigation_service_systemd.sh"
  fi
  if (( RUN_RADIO )); then
    OPENROADCODE_PYTHON="$python_bin" OPENROADCODE_MANAGED_RF="$MANAGED_RF" \
      bash "$PROJECT_ROOT/scripts/systemd/install_sdrforge_user_systemd.sh"
  fi
fi
