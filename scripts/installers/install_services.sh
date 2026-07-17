#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$PROJECT_ROOT}"
GPS_DEVICE="${GPS_DEVICE:-/dev/ttyACM0}"

RUN_VNC=1
RUN_GPSD_SERVICE=1

for arg in "$@"; do
  case "$arg" in
    0|false|no)
      ;;
    1|true|yes)
      ;;
    *)
      ;;
  esac
done

if [[ $# -ge 1 ]]; then
  RUN_VNC="$1"
fi
if [[ $# -ge 2 ]]; then
  RUN_GPSD_SERVICE="$2"
fi

echo "[*] Granting user permissions..."
sudo usermod -aG input   "$USER"
sudo usermod -aG dialout "$USER"

if [[ "$RUN_VNC" != "0" ]]; then
  echo "[*] Setting up VNC..."
  bash "$PROJECT_ROOT/scripts/installers/setup_vnc.sh"
fi

if [[ "$RUN_GPSD_SERVICE" != "0" ]]; then
  echo "[*] Installing GPS systemd service..."
  sudo bash "$PROJECT_ROOT/scripts/systemd/install_gpsd_systemd.sh" "$GPS_DEVICE"
fi
