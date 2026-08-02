#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

if ! command -v whiptail >/dev/null 2>&1; then
  echo "[!] whiptail is not installed. Install it with: sudo apt install -y whiptail" >&2
  exit 1
fi

selection="$(
  whiptail --title "OpenRoadCode uninstaller" --checklist \
    "Select components to remove. Shared packages and user data are preserved." \
    18 82 8 \
    "venv" "Project Python virtual environment" ON \
    "vnc" "carui-vnc user service" ON \
    "gpsd" "gpsd-start system service" ON \
    "rfcomm" "OpenRoadCode ELM327 RFCOMM services" ON \
    3>&1 1>&2 2>&3
)" || exit 0

selection="${selection//\"/}"
if [[ -z "$selection" ]]; then
  whiptail --title "OpenRoadCode uninstaller" \
    --msgbox "Nothing was selected. No changes were made." 9 54
  exit 0
fi

summary="Selected components:\n"
args=()
for component in $selection; do
  case "$component" in
    venv)
      args+=(--venv)
      summary+="\n- Project virtual environment"
      ;;
    vnc)
      args+=(--vnc-service)
      summary+="\n- VNC user service"
      ;;
    gpsd)
      args+=(--gpsd-service)
      summary+="\n- GPS system service"
      ;;
    rfcomm)
      args+=(--rfcomm-services)
      summary+="\n- ELM327 RFCOMM services"
      ;;
  esac
done

summary+="\n\nApt packages, group memberships, Bluetooth pairings, ~/.vnc,"
summary+=" and project files will be preserved.\n\nContinue?"
if ! whiptail --title "Confirm uninstall" --yesno "$summary" 19 76; then
  exit 0
fi

bash "$SCRIPT_DIR/uninstall.sh" --yes "${args[@]}"
