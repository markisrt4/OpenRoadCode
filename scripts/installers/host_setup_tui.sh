#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$PROJECT_ROOT}"

if ! command -v whiptail >/dev/null 2>&1; then
  echo "[!] whiptail is not installed. Install it with: sudo apt install -y whiptail"
  exit 1
fi

if whiptail --title "OpenRoadCode Raspberry Pi installer" --yesno "Would you like to run the interactive installer?" 10 60; then
  :
else
  exit 0
fi

SELECTED_GENERAL="base"
SELECTED_STREAMING="streamlit"
SELECTED_NAVIGATION="gps"
SELECTED_RADIO=""
SELECTED_AUTOMOTIVE="elm327"
SELECTED_BLUETOOTH="bluetooth"
SELECTED_BAROMETRIC=""
ELM327_ADDRESS=""

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

choose_barometric_sensor() {
  local selection
  selection=$(whiptail --title "Barometric sensor" --radiolist \
    "Select one barometric sensor driver:" 14 76 4 \
    "none" "Do not install a barometric sensor driver" \
      "$([[ -z "$SELECTED_BAROMETRIC" ]] && echo ON || echo OFF)" \
    "bmp388" "Bosch BMP388" \
      "$([[ "$SELECTED_BAROMETRIC" == "bmp388" ]] && echo ON || echo OFF)" \
    "bmp390" "Bosch BMP390" \
      "$([[ "$SELECTED_BAROMETRIC" == "bmp390" ]] && echo ON || echo OFF)" \
    3>&1 1>&2 2>&3) || return 1

  if [[ "$selection" == "none" ]]; then
    SELECTED_BAROMETRIC=""
  else
    SELECTED_BAROMETRIC="$selection"
  fi
}

while true; do
  section=$(whiptail --title "OpenRoadCode installer" --menu \
    "Choose a section to configure, then select Install:" 20 76 9 \
    "general" "General features" \
    "streaming" "Streaming" \
    "navigation" "Navigation" \
    "environmental" "Environmental sensors" \
    "radio" "Radio" \
    "automotive" "Automotive devices" \
    "bluetooth" "Bluetooth" \
    "install" "Install the selected features" \
    "cancel" "Exit without installing" \
    3>&1 1>&2 2>&3) || exit 0

  case "$section" in
    general)
      choose_features "General features" "Select general features:" "$SELECTED_GENERAL" \
        "base|Core system dependencies" \
        "core-ui|Browser/UI support" && SELECTED_GENERAL="$SELECTED_RESULT"
      ;;
    streaming)
      choose_features "Streaming" "Select streaming features:" "$SELECTED_STREAMING" \
        "streamlit|Streamlit dashboard support" \
        "spotify|Spotify integration" && SELECTED_STREAMING="$SELECTED_RESULT"
      ;;
    navigation)
      choose_features "Navigation" "Select GPS support and navigation hardware:" "$SELECTED_NAVIGATION" \
        "gps|GPS daemon and Python support" \
        "mpu6050|MPU6050 accelerometer/gyroscope" && SELECTED_NAVIGATION="$SELECTED_RESULT"
      ;;
    environmental)
      choose_barometric_sensor
      ;;
    radio)
      choose_features "Radio" "Select radio features:" "$SELECTED_RADIO" \
        "adsb|ADS-B/readsb support" \
        "sdrpp|SDR++ support" && SELECTED_RADIO="$SELECTED_RESULT"
      ;;
    automotive)
      choose_features "Automotive" "Select automotive devices:" "$SELECTED_AUTOMOTIVE" \
        "elm327|ELM327 serial device (hardware_io/automotive/elm327)" && SELECTED_AUTOMOTIVE="$SELECTED_RESULT"
      ;;
    bluetooth)
      choose_features "Bluetooth" "Select Bluetooth features:" "$SELECTED_BLUETOOTH" \
        "bluetooth|Bluetooth device support" && SELECTED_BLUETOOTH="$SELECTED_RESULT"
      ;;
    install)
      break
      ;;
    cancel)
      exit 0
      ;;
  esac
done

if [[ " $SELECTED_AUTOMOTIVE " == *" elm327 "* ]]; then
  if whiptail --title "ELM327 RFCOMM" --yesno \
    "Discover, pair, and configure a Bluetooth ELM327 device now?" 10 68; then
    ELM327_ADDRESS="$(
      whiptail --title "ELM327 RFCOMM" --inputbox \
        "Enter the ELM327 Bluetooth MAC address:" 10 68 \
        3>&1 1>&2 2>&3
    )" || ELM327_ADDRESS=""
  fi
fi

ARGS=()
for feature in \
  ${SELECTED_GENERAL} \
  ${SELECTED_STREAMING} \
  ${SELECTED_NAVIGATION} \
  ${SELECTED_BAROMETRIC} \
  ${SELECTED_RADIO} \
  ${SELECTED_AUTOMOTIVE} \
  ${SELECTED_BLUETOOTH}; do
  ARGS+=(--feature "$feature")
done

if [[ " $SELECTED_GENERAL " != *" base "* ]]; then
  ARGS+=(--feature base)
fi

if [[ " $SELECTED_RADIO " == *" sdrpp "* ]]; then
  ARGS+=(--install-sdrpp)
fi

if [[ -n "$ELM327_ADDRESS" ]]; then
  ARGS+=(--elm327-address "$ELM327_ADDRESS")
fi

bash "$PROJECT_DIR/scripts/installers/host_setup.sh" "${ARGS[@]}"
