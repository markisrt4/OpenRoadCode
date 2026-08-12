#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$PROJECT_ROOT}"

if ! command -v whiptail >/dev/null 2>&1; then
  echo "[!] whiptail is not installed. Install it with: sudo apt install -y whiptail"
  exit 1
fi

if whiptail --title "OpenRoadCode installer" --yesno "Would you like to run the interactive installer?" 10 60; then
  :
else
  exit 0
fi

SELECTED_TARGET="$(
  whiptail --title "Installation target" --radiolist \
    "Choose the system profile to install:" 15 78 5 \
    "rpi4" "Raspberry Pi 4 or Compute Module 4" OFF \
    "rpi5" "Raspberry Pi 5, Pi 500, or Compute Module 5" OFF \
    "linux-dev" "Debian/Ubuntu development workstation or VM" ON \
    3>&1 1>&2 2>&3
)" || exit 0

SELECTED_GENERAL="base"
SELECTED_STREAMING=""
SELECTED_NAVIGATION=""
SELECTED_RADIO=""
SELECTED_AUTOMOTIVE=""
SELECTED_BLUETOOTH=""
SELECTED_ENVIRONMENTAL=""
INSTALL_ALL_FEATURES=0

choose_features() {
  local title="$1"
  local prompt="$2"
  local selected="$3"
  shift 3

  local options=()
  local entry feature description state selection
  for entry in "$@"; do
    feature="${entry%%|*}"
    description="${entry#*|}"
    state=OFF
    if [[ " $selected " == *" $feature "* ]]; then
      state=ON
    fi
    options+=("$feature" "$description" "$state")
  done

  selection=$(whiptail --title "$title" --checklist \
    "$prompt" 20 90 10 \
    "${options[@]}" 3>&1 1>&2 2>&3) || return 1
  SELECTED_RESULT="${selection//\"/}"
}

while true; do
  section=$(whiptail --title "OpenRoadCode installer" --menu \
    "Choose a section to configure, then select Install:" 21 76 10 \
    "general" "General features" \
    "streaming" "Streaming" \
    "navigation" "Navigation" \
    "environmental" "Environmental sensors" \
    "radio" "Radio" \
    "automotive" "Automotive devices" \
    "bluetooth" "Bluetooth" \
    "all" "Install every capability compatible with the target" \
    "install" "Install the selected features" \
    "cancel" "Exit without installing" \
    3>&1 1>&2 2>&3) || exit 0

  case "$section" in
    general)
      choose_features "General features" "Select general features:" "$SELECTED_GENERAL" \
        "base|Portable command-line runtime" \
        "desktop-ui|Tk, X11, Openbox, and XFCE support" \
        "browser|Chromium browser support" \
        "vnc|TigerVNC server support" \
        "input|Linux input/evdev support" && SELECTED_GENERAL="$SELECTED_RESULT"
      ;;
    streaming)
      choose_features "Streaming" "Select streaming features:" "$SELECTED_STREAMING" \
        "streamlit|Streamlit dashboard support" \
        "spotify|Spotify integration" && SELECTED_STREAMING="$SELECTED_RESULT"
      ;;
    navigation)
      choose_features "Navigation" "Select GPS support and navigation hardware:" "$SELECTED_NAVIGATION" \
        "gps|GPS daemon and Python support" \
        "imu|Generic inertial-sensor tooling" && SELECTED_NAVIGATION="$SELECTED_RESULT"
      ;;
    environmental)
      choose_features "Environmental" "Select environmental capabilities:" "$SELECTED_ENVIRONMENTAL" \
        "environmental|Generic environmental-sensor tooling" && SELECTED_ENVIRONMENTAL="$SELECTED_RESULT"
      ;;
    radio)
      choose_features "Radio" "Select radio features:" "$SELECTED_RADIO" \
        "rtl-sdr|RTL-SDR and SoapySDR support" \
        "adsb|ADS-B/readsb support" \
        "sdrpp|SDR++ support" && SELECTED_RADIO="$SELECTED_RESULT"
      ;;
    automotive)
      choose_features "Automotive" "Select automotive devices:" "$SELECTED_AUTOMOTIVE" \
        "automotive|Generic serial and CAN-bus support" && SELECTED_AUTOMOTIVE="$SELECTED_RESULT"
      ;;
    bluetooth)
      choose_features "Bluetooth" "Select Bluetooth features:" "$SELECTED_BLUETOOTH" \
        "bluetooth|Bluetooth device support" && SELECTED_BLUETOOTH="$SELECTED_RESULT"
      ;;
    all)
      INSTALL_ALL_FEATURES=1
      SELECTED_GENERAL="vnc"
      SELECTED_NAVIGATION="gps"
      SELECTED_BLUETOOTH="bluetooth"
      break
      ;;
    install)
      break
      ;;
    cancel)
      exit 0
      ;;
  esac
done

ARGS=(--target "$SELECTED_TARGET" --no-default-features)
if (( INSTALL_ALL_FEATURES )); then
  ARGS+=(--all-features)
else
  for feature in \
    ${SELECTED_GENERAL} \
    ${SELECTED_STREAMING} \
    ${SELECTED_NAVIGATION} \
    ${SELECTED_ENVIRONMENTAL} \
    ${SELECTED_RADIO} \
    ${SELECTED_AUTOMOTIVE} \
    ${SELECTED_BLUETOOTH}; do
    ARGS+=(--feature "$feature")
  done

  if [[ " $SELECTED_GENERAL " != *" base "* ]]; then
    ARGS+=(--feature base)
  fi
fi

if [[ " $SELECTED_GENERAL " == *" vnc "* ]]; then
  if whiptail --title "VNC service" --yesno \
    "Configure and enable the VNC service after installing it?" 10 68; then
    ARGS+=(--with-vnc)
  fi
fi

if [[ " $SELECTED_NAVIGATION " == *" gps "* ]]; then
  if whiptail --title "GPSD service" --yesno \
    "Configure the default GPSD service after installing GPS support?" 10 72; then
    ARGS+=(--with-gpsd-service)
  fi
fi

bash "$PROJECT_DIR/scripts/installers/host_setup.sh" "${ARGS[@]}"

if [[ " $SELECTED_BLUETOOTH " == *" bluetooth "* ]]; then
  if whiptail --title "Post-install configuration" --yesno \
    "Configure a Bluetooth Serial Port Profile device now?" 10 72; then
    bash "$PROJECT_DIR/scripts/installers/setup_bluetooth_spp.sh"
  fi
fi
