#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$PROJECT_ROOT}"
VENV_DIR="${VENV_DIR:-$PROJECT_DIR/venv}"

REMOVE_VENV=0
REMOVE_VNC_SERVICE=0
REMOVE_GPSD_SERVICE=0
REMOVE_RFCOMM_SERVICES=0
ASSUME_YES=0

usage() {
  cat <<'EOF'
Usage: uninstall.sh [options]

Remove components created by the OpenRoadCode installer. Shared apt packages,
user group memberships, Bluetooth pairings, and VNC user data are preserved.

Options:
  --venv              Remove the project virtual environment
  --vnc-service       Remove the carui-vnc user service
  --gpsd-service      Remove the gpsd-start system service
  --rfcomm-services   Remove OpenRoadCode RFCOMM system services
  --all               Select all of the above
  -y, --yes           Do not prompt for confirmation
  -h, --help          Show this help
EOF
}

while (( $# > 0 )); do
  case "$1" in
    --venv)
      REMOVE_VENV=1
      ;;
    --vnc-service)
      REMOVE_VNC_SERVICE=1
      ;;
    --gpsd-service)
      REMOVE_GPSD_SERVICE=1
      ;;
    --rfcomm-services)
      REMOVE_RFCOMM_SERVICES=1
      ;;
    --all)
      REMOVE_VENV=1
      REMOVE_VNC_SERVICE=1
      REMOVE_GPSD_SERVICE=1
      REMOVE_RFCOMM_SERVICES=1
      ;;
    -y|--yes)
      ASSUME_YES=1
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

if (( ! REMOVE_VENV && ! REMOVE_VNC_SERVICE && ! REMOVE_GPSD_SERVICE && ! REMOVE_RFCOMM_SERVICES )); then
  echo "[!] Nothing selected for removal." >&2
  usage >&2
  exit 1
fi

echo "[*] OpenRoadCode uninstall selection:"
(( REMOVE_VENV )) && echo "    Project venv:       $VENV_DIR"
(( REMOVE_VNC_SERVICE )) && echo "    User service:       carui-vnc.service"
(( REMOVE_GPSD_SERVICE )) && echo "    System service:     gpsd-start.service"
(( REMOVE_RFCOMM_SERVICES )) && echo "    System services:    openroadcode-rfcomm*.service"
echo
echo "[*] Apt packages, group memberships, Bluetooth pairings, ~/.vnc,"
echo "    and project source files will not be removed."

if (( ! ASSUME_YES )); then
  read -r -p "Continue? [y/N] " answer
  case "$answer" in
    y|Y|yes|YES)
      ;;
    *)
      echo "[*] Uninstall cancelled."
      exit 0
      ;;
  esac
fi

if (( REMOVE_VNC_SERVICE )); then
  vnc_service_file="$HOME/.config/systemd/user/carui-vnc.service"
  systemctl --user disable --now carui-vnc.service >/dev/null 2>&1 || true
  if [[ -f "$vnc_service_file" ]]; then
    rm -- "$vnc_service_file"
    echo "[+] Removed $vnc_service_file"
  else
    echo "[*] VNC user service is not installed."
  fi
  systemctl --user daemon-reload >/dev/null 2>&1 || true
fi

if (( REMOVE_GPSD_SERVICE )); then
  gpsd_service_file="/etc/systemd/system/gpsd-start.service"
  sudo systemctl disable --now gpsd-start.service >/dev/null 2>&1 || true
  if sudo test -f "$gpsd_service_file"; then
    sudo rm -- "$gpsd_service_file"
    echo "[+] Removed $gpsd_service_file"
  else
    echo "[*] OpenRoadCode GPS service is not installed."
  fi
  sudo systemctl daemon-reload
fi

if (( REMOVE_RFCOMM_SERVICES )); then
  rfcomm_service_found=0
  for service_file in /etc/systemd/system/openroadcode-rfcomm*.service; do
    [[ -f "$service_file" ]] || continue
    service_name="${service_file##*/}"
    if [[ ! "$service_name" =~ ^openroadcode-rfcomm[0-9]+\.service$ ]]; then
      echo "[!] Refusing unexpected RFCOMM service name: $service_name" >&2
      continue
    fi

    rfcomm_service_found=1
    sudo systemctl disable --now "$service_name" >/dev/null 2>&1 || true
    sudo rm -- "$service_file"
    echo "[+] Removed $service_file"
  done
  if (( ! rfcomm_service_found )); then
    echo "[*] No OpenRoadCode RFCOMM services are installed."
  fi
  sudo systemctl daemon-reload
fi

if (( REMOVE_VENV )); then
  project_real="$(realpath -m -- "$PROJECT_DIR")"
  venv_real="$(realpath -m -- "$VENV_DIR")"

  if [[ "$venv_real" != "$project_real"/* ]]; then
    echo "[!] Refusing to remove a venv outside the project: $venv_real" >&2
    exit 1
  elif [[ ! -e "$venv_real" ]]; then
    echo "[*] Project venv does not exist."
  elif [[ ! -f "$venv_real/pyvenv.cfg" ]]; then
    echo "[!] Refusing to remove a directory without pyvenv.cfg: $venv_real" >&2
    exit 1
  else
    rm -rf -- "$venv_real"
    echo "[+] Removed project venv: $venv_real"
  fi
fi

echo "[+] OpenRoadCode uninstall complete."
