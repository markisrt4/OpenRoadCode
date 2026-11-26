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

NAVIGATION_MODE=auto
NAVIGATION_REGION=none
WITH_NAVIGATION=1
SELECTED_TARGET=linux-dev
SELECTED_GENERAL="base"
SELECTED_STREAMING=""
SELECTED_AUDIO=""
SELECTED_NAVIGATION=""
SELECTED_RADIO="sdrforge"
SELECTED_VIDEO=""
SELECTED_AUTOMOTIVE=""
SELECTED_BLUETOOTH=""
SELECTED_ENVIRONMENTAL=""
INSTALL_ALL_FEATURES=0
WITH_VNC=0
WITH_ORC_AUTOSTART=0
WITH_GPSD=0
WITH_TELEMETRY=0
WITH_RADIO=1
SETTINGS_FILE="${XDG_CONFIG_HOME:-$HOME/.config}/openroadcode/installer-selection.conf"
settings_keys=(NAVIGATION_MODE NAVIGATION_REGION WITH_NAVIGATION SELECTED_TARGET SELECTED_GENERAL SELECTED_STREAMING SELECTED_AUDIO SELECTED_NAVIGATION SELECTED_RADIO SELECTED_VIDEO SELECTED_AUTOMOTIVE SELECTED_BLUETOOTH SELECTED_ENVIRONMENTAL INSTALL_ALL_FEATURES WITH_VNC WITH_ORC_AUTOSTART WITH_GPSD WITH_TELEMETRY WITH_RADIO)
if [[ -f "$SETTINGS_FILE" ]]; then
  while IFS='=' read -r key value; do
    case "$key" in
      NAVIGATION_REGION) [[ "$value" =~ ^[a-z0-9/-]+$ ]] && NAVIGATION_REGION="$value" ;;
      NAVIGATION_MODE) case "$value" in auto|binary|source) NAVIGATION_MODE="$value" ;; esac ;;
      SELECTED_TARGET) case "$value" in rpi4|rpi5|linux-dev) SELECTED_TARGET="$value" ;; esac ;;
      INSTALL_ALL_FEATURES|WITH_NAVIGATION|WITH_VNC|WITH_ORC_AUTOSTART|WITH_GPSD|WITH_TELEMETRY|WITH_RADIO)
        [[ "$value" == 0 || "$value" == 1 ]] && printf -v "$key" '%s' "$value" ;;
      SELECTED_GENERAL|SELECTED_STREAMING|SELECTED_AUDIO|SELECTED_NAVIGATION|SELECTED_RADIO|SELECTED_VIDEO|SELECTED_AUTOMOTIVE|SELECTED_BLUETOOTH|SELECTED_ENVIRONMENTAL)
        [[ "$value" =~ ^[a-z0-9[:space:]-]*$ ]] && printf -v "$key" '%s' "$value" ;;
    esac
  done < "$SETTINGS_FILE"
fi
# Retire Streamlit from interactive selections; legacy CLI remains available.
SELECTED_STREAMING=" $SELECTED_STREAMING "
SELECTED_STREAMING="${SELECTED_STREAMING/ streamlit / }"
SELECTED_STREAMING="${SELECTED_STREAMING# }"
SELECTED_STREAMING="${SELECTED_STREAMING% }"
# Migrate audio selections saved by older versions of the streaming menu.
if [[ " $SELECTED_STREAMING " == *" audio "* ]]; then
  [[ " $SELECTED_AUDIO " == *" audio "* ]] || SELECTED_AUDIO="${SELECTED_AUDIO:+$SELECTED_AUDIO }audio"
  SELECTED_STREAMING=" ${SELECTED_STREAMING} "
  SELECTED_STREAMING="${SELECTED_STREAMING/ audio / }"
  SELECTED_STREAMING="${SELECTED_STREAMING# }"
  SELECTED_STREAMING="${SELECTED_STREAMING% }"
fi

save_settings() {
  local key temporary
  mkdir -p "$(dirname "$SETTINGS_FILE")"
  temporary="$(mktemp "${SETTINGS_FILE}.XXXXXX")"
  for key in "${settings_keys[@]}"; do
    printf '%s=%s\n' "$key" "${!key}"
  done > "$temporary"
  mv -f -- "$temporary" "$SETTINGS_FILE"
}

target_state() {
  if [[ "$SELECTED_TARGET" == "$1" ]]; then echo ON; else echo OFF; fi
}

SELECTED_TARGET="$(whiptail --title "Installation target" --radiolist \
  "Choose the system profile to install:" 15 78 5 \
  "rpi4" "Raspberry Pi 4 or Compute Module 4" "$(target_state rpi4)" \
  "rpi5" "Raspberry Pi 5, Pi 500, or Compute Module 5" "$(target_state rpi5)" \
  "linux-dev" "Debian/Ubuntu development workstation or VM" "$(target_state linux-dev)" \
  3>&1 1>&2 2>&3)" || exit 0

choose_features() {
  local title="$1" prompt="$2" selected="$3"
  shift 3
  local options=() entry feature description state selection
  for entry in "$@"; do
    feature="${entry%%|*}"; description="${entry#*|}"; state=OFF
    [[ " $selected " == *" $feature "* ]] && state=ON
    options+=("$feature" "$description" "$state")
  done
  selection=$(whiptail --title "$title" --checklist "$prompt" 20 90 10 "${options[@]}" 3>&1 1>&2 2>&3) || return 1
  SELECTED_RESULT="${selection//\"/}"
}

build_feature_args() {
  ARGS=(--target "$SELECTED_TARGET" --no-default-features)
  if (( INSTALL_ALL_FEATURES )); then
    ARGS+=(--all-features)
  else
    for feature in ${SELECTED_GENERAL} ${SELECTED_STREAMING} ${SELECTED_AUDIO} ${SELECTED_NAVIGATION} ${SELECTED_ENVIRONMENTAL} ${SELECTED_RADIO} ${SELECTED_VIDEO} ${SELECTED_AUTOMOTIVE} ${SELECTED_BLUETOOTH}; do
      ARGS+=(--feature "$feature")
    done
    [[ " $SELECTED_GENERAL " == *" base "* ]] || ARGS+=(--feature base)
  fi
}

show_installation_inventory() {
  local report python_bin feature action destination
  local software=ON services=ON
  local -a packages filters
  python_bin="${VENV_DIR:-$PROJECT_DIR/venv}/bin/python"
  if [[ ! -x "$python_bin" ]]; then
    if [[ -x "$PROJECT_DIR/../.venv/bin/python" ]]; then
      python_bin="$PROJECT_DIR/../.venv/bin/python"
    elif [[ -x "$PROJECT_DIR/.venv/bin/python" ]]; then
      python_bin="$PROJECT_DIR/.venv/bin/python"
    else
      python_bin=python3
    fi
  fi
  mapfile -t packages < <(
    source "$SCRIPT_DIR/installer_features.sh"
    while read -r feature; do get_feature_packages "$feature"; done < <(get_known_features) |
      tr -s '[:space:]' '\n' | sort -u
  )
  while true; do
    action="$(whiptail --title "Installed software and services" --menu \
      "Choose sections to include, view the inventory, or export it." 16 78 4 \
      software "Show software: $software" \
      services "Show services: $services" \
      view "View inventory" \
      export "Export inventory to a text file" \
      3>&1 1>&2 2>&3)" || return 0
    case "$action" in
      software) if [[ "$software" == ON ]]; then software=OFF; else software=ON; fi; continue ;;
      services) if [[ "$services" == ON ]]; then services=OFF; else services=ON; fi; continue ;;
      export)
        destination="$(whiptail --title "Export inventory" --inputbox \
          "Save the selected inventory sections to this file:" 11 78 \
          "$PWD/openroadcode-inventory-$(date +%Y%m%d-%H%M%S).txt" 3>&1 1>&2 2>&3)" || continue
        [[ -n "$destination" ]] || continue
        ;;
    esac

    filters=()
    if [[ "$software" == OFF ]]; then filters+=(--hide-software); fi
    if [[ "$services" == OFF ]]; then filters+=(--hide-services); fi
    report="$(mktemp -t openroadcode-inventory.XXXXXX)"
    (cd "$PROJECT_DIR" && "$python_bin" -m scripts.installers.installation_inventory "${filters[@]}" -- "${packages[@]}") >"$report" 2>&1 ||
      printf '\nInventory could not finish. See the output above.\n' >>"$report"
    if [[ "$action" == export ]]; then
      if (umask 077; set -o noclobber; cat -- "$report" >"$destination"); then
        whiptail --title "Inventory exported" --msgbox "Saved to $destination" 10 78 || true
      else
        whiptail --title "Export failed" --msgbox "Could not create $destination. Choose a new filename in a writable directory." 11 78 || true
      fi
    else
      whiptail --title "Installation inventory" --scrolltext --textbox "$report" 20 78 || true
    fi
    rm -f -- "$report"
  done
}

verify_current_installation() {
  local report status=0
  build_feature_args
  if [[ " $SELECTED_NAVIGATION " == *" navigation "* ]] || { (( INSTALL_ALL_FEATURES )) && [[ "$SELECTED_TARGET" != linux-dev ]]; }; then
    if [[ "$NAVIGATION_REGION" != none ]]; then ARGS+=(--navigation-region "$NAVIGATION_REGION"); fi
    if (( WITH_NAVIGATION )); then ARGS+=(--with-navigation-service); else ARGS+=(--no-navigation-service); fi
  fi
  if [[ " $SELECTED_RADIO $SELECTED_GENERAL " == *" sdrforge "* ]] || (( INSTALL_ALL_FEATURES )); then
    if (( WITH_RADIO )); then ARGS+=(--with-radio-service); else ARGS+=(--no-radio-service); fi
  fi
  if (( WITH_GPSD )); then ARGS+=(--with-gpsd-service); else ARGS+=(--no-gpsd-service); fi
  if (( WITH_VNC )) && { [[ " $SELECTED_GENERAL " == *" vnc "* ]] || (( INSTALL_ALL_FEATURES )); }; then
    ARGS+=(--with-vnc)
  fi
  if (( WITH_TELEMETRY )); then ARGS+=(--with-telemetry-services); fi
  report="$(mktemp -t openroadcode-verify.XXXXXX)"
  OPENROAD_RUNTIME_REPORT= bash "$PROJECT_DIR/scripts/installers/host_setup.sh" "${ARGS[@]}" --verify-only >"$report" 2>&1 || status=$?
  printf '\nVerification exit status: %s\n' "$status" >> "$report"
  whiptail --title "Current installation verification" --scrolltext --textbox "$report" 20 78 || true
  rm -f -- "$report"
}

while true; do
  section=$(whiptail --title "OpenRoadCode installer" --default-item install --menu \
    "Choose a section to configure, then select Install:" 24 76 12 \
    "general" "General features and user interfaces" \
    "streaming" "Streaming and media" \
    "audio" "Audio output and Bluetooth speakers" \
    "navigation" "Navigation" \
    "environmental" "Environmental sensors" \
    "radio" "Radio" \
    "video" "Video and camera perception" \
    "automotive" "Automotive devices" \
    "bluetooth" "Bluetooth" \
    "all" "Select every capability compatible with the target" \
    "inventory" "Show installed software and services" \
    "install" "Install or verify the selected features" \
    "cancel" "Exit without installing" 3>&1 1>&2 2>&3) || exit 0
  case "$section" in
    all|inventory|install|cancel) ;;
    *) INSTALL_ALL_FEATURES=0 ;;
  esac
  case "$section" in
    general) choose_features "General features" "Select general features and user interfaces:" "$SELECTED_GENERAL" \
      "base|Portable command-line runtime and ZeroMQ messaging" \
      "desktop-ui|Tk, X11, Openbox, and XFCE support" \
      "web-ui|Flask-based OpenRoadCode web UI" \
      "browser|Chromium browser support" \
      "vnc|TigerVNC server support" \
      "input|Linux input/evdev support" && SELECTED_GENERAL="$SELECTED_RESULT" ;;
    audio) choose_features "Audio configuration" "Select playback capabilities. USB, HDMI and supported analog outputs share the same audio infrastructure:" "$SELECTED_AUDIO" \
      "audio|PipeWire and ALSA (USB, HDMI, supported analog)" \
      "audio-bluetooth|Bluetooth speakers and headphones (includes audio)" && SELECTED_AUDIO="$SELECTED_RESULT" ;;
    streaming) choose_features "Streaming and media" "Select media features:" "$SELECTED_STREAMING" \
      "spotify|Spotify integration" \
      "youtube|YouTube music video integration" && SELECTED_STREAMING="$SELECTED_RESULT" ;;
    navigation) choose_features "Navigation" "Select navigation software and positioning hardware:" "$SELECTED_NAVIGATION" \
      "navigation|Native MapLibre and Valhalla navigation stack" \
      "gps|GPS daemon and Python support" \
      "imu|MPU-6050 inertial sensor support" && SELECTED_NAVIGATION="$SELECTED_RESULT" ;;
    environmental) choose_features "Environmental" "Select environmental capabilities:" "$SELECTED_ENVIRONMENTAL" \
      "environmental|BMP388/BMP390 pressure and temperature support" && SELECTED_ENVIRONMENTAL="$SELECTED_RESULT" ;;
    radio) choose_features "Radio" "Select radio features:" "$SELECTED_RADIO" \
      "rtl-sdr|RTL-SDR and SoapySDR support" \
      "adsb|ADS-B/readsb support" \
      "sdrforge|Native SDRForge radio" && SELECTED_RADIO="$SELECTED_RESULT" ;;
    video) choose_features "Video" "Select camera and perception capabilities:" "$SELECTED_VIDEO" \
      "video|Common camera capture and preview" \
      "video-v4l2|Linux USB cameras and V4L2 controls" \
      "video-perception|YOLO object detection and tracking" && SELECTED_VIDEO="$SELECTED_RESULT" ;;
    automotive) choose_features "Automotive" "Select automotive devices:" "$SELECTED_AUTOMOTIVE" \
      "automotive|Generic serial and CAN-bus support" && SELECTED_AUTOMOTIVE="$SELECTED_RESULT" ;;
    bluetooth) choose_features "Bluetooth" "Select Bluetooth features:" "$SELECTED_BLUETOOTH" \
      "bluetooth|Bluetooth device support" && SELECTED_BLUETOOTH="$SELECTED_RESULT" ;;
    inventory) show_installation_inventory ;;
    all|install)
      if [[ "$section" == all ]]; then INSTALL_ALL_FEATURES=1; fi
      while true; do
        action="$(whiptail --title "Installation options" --menu \
          "Choose what to do with the selected setup:" 14 76 3 \
          install "Install the selected features" \
          verify "Verify the existing installation against this selection" \
          back "Return to feature selection" 3>&1 1>&2 2>&3)" || break
        case "$action" in
          install) break 2 ;;
          verify) verify_current_installation ;;
          back) break ;;
        esac
      done
      ;;
    cancel) exit 0 ;;
  esac
done

build_feature_args

if [[ " $SELECTED_NAVIGATION " == *" navigation "* ]] || { (( INSTALL_ALL_FEATURES )) && [[ "$SELECTED_TARGET" != linux-dev ]]; }; then
  NAVIGATION_MODE="$(whiptail --title "Navigation installation" --default-item "$NAVIGATION_MODE" --menu \
    "Choose how to install native navigation:" 15 78 3 \
    auto "Prefer prebuilt binaries; source fallback if unavailable" \
    binary "Require prebuilt binaries; never compile" \
    source "Build from source when needed" 3>&1 1>&2 2>&3)" || exit 0
fi
ARGS+=(--navigation-mode "$NAVIGATION_MODE")

NAVIGATION_SELECTED=0
if [[ " $SELECTED_NAVIGATION " == *" navigation "* ]] || { (( INSTALL_ALL_FEATURES )) && [[ "$SELECTED_TARGET" != linux-dev ]]; }; then
  NAVIGATION_SELECTED=1
  catalog_rows="$(python3 - "$PROJECT_DIR/scripts/runtime/navigation-data-catalog.json" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as stream:
    catalog = json.load(stream)
for region, entry in sorted(catalog["regions"].items()):
    print(f"{region}\t{entry['title']} ({entry['archive_bytes'] / 1024**3:.2f} GiB download)")
PY
)"
  region_options=(none "Skip regional data; manage datasets separately")
  region_default=none
  while IFS=$'\t' read -r region description; do
    [[ -n "$region" ]] || continue
    region_options+=("$region" "$description")
    [[ "$region" != "$NAVIGATION_REGION" ]] || region_default="$region"
  done <<< "$catalog_rows"
  NAVIGATION_REGION="$(whiptail --title "Offline navigation data" --default-item "$region_default" --menu \
    "Select a regional dataset. Downloads are cached and verified before deployment." 18 78 8 \
    "${region_options[@]}" 3>&1 1>&2 2>&3)" || exit 0
  if [[ "$NAVIGATION_REGION" != none ]]; then
    ARGS+=(--navigation-region "$NAVIGATION_REGION")
  fi
fi

ask_service() {
  local variable="$1" title="$2" prompt="$3"
  local options=()
  if [[ "${!variable}" == 0 ]]; then options+=(--defaultno); fi
  if whiptail --title "$title" "${options[@]}" --yesno "$prompt" 14 78; then
    printf -v "$variable" 1
  else
    printf -v "$variable" 0
  fi
}

if [[ " $SELECTED_GENERAL " == *" vnc "* ]] || (( INSTALL_ALL_FEATURES )); then
  ask_service WITH_VNC "VNC service" "Configure and enable the VNC service?"
else
  WITH_VNC=0
fi
if [[ " $SELECTED_NAVIGATION " == *" gps "* || " $SELECTED_NAVIGATION " == *" navigation "* ]] || (( INSTALL_ALL_FEATURES )); then
  ask_service WITH_GPSD "GPSD service" "Configure the default GPSD service?"
else
  WITH_GPSD=0
fi
if [[ "$SELECTED_TARGET" != termux ]] && { (( INSTALL_ALL_FEATURES )) || [[ " $SELECTED_RADIO $SELECTED_GENERAL " == *" sdrforge "* ]]; }; then
  ask_service WITH_RADIO "Native radio service" "Enable SDRForge and the ZeroMQ message broker at startup?"
  if (( WITH_RADIO )); then ARGS+=(--with-radio-service); else ARGS+=(--no-radio-service); fi
fi
if (( NAVIGATION_SELECTED )); then
  ask_service WITH_NAVIGATION "Navigation services" "Enable the message broker and navigation controller at startup?"
  if (( WITH_NAVIGATION )); then ARGS+=(--with-navigation-service); else ARGS+=(--no-navigation-service); fi
fi
ask_service WITH_TELEMETRY "OpenRoadCode telemetry" "Configure and enable the ZeroMQ broker, navigation producer, and automotive producer services?"
if (( WITH_VNC )); then ARGS+=(--with-vnc); fi
if (( WITH_GPSD )); then ARGS+=(--with-gpsd-service); else ARGS+=(--no-gpsd-service); fi
if (( WITH_TELEMETRY )); then ARGS+=(--with-telemetry-services); fi

ask_service WITH_ORC_AUTOSTART "ORC desktop autostart" \
  "Launch OpenRoadCode when this user signs into the desktop? On a Pi with desktop auto-login, ORC will launch after boot."
if (( WITH_ORC_AUTOSTART )); then
  ARGS+=(--with-orc-autostart)
else
  ARGS+=(--no-orc-autostart)
fi

save_settings
runtime_report="$(mktemp -t openroadcode-runtime.XXXXXX)"
trap 'rm -f -- "$runtime_report"' EXIT
while true; do
  : > "$runtime_report"
  status=0
  OPENROAD_RUNTIME_REPORT="$runtime_report" \
    bash "$PROJECT_DIR/scripts/installers/host_setup.sh" "${ARGS[@]}" || status=$?
  if [[ -s "$runtime_report" ]]; then
    whiptail --title "Runtime verification results" --scrolltext \
      --textbox "$runtime_report" 20 78 || true
  elif (( status != 0 )) && [[ "$SELECTED_TARGET" != termux ]]; then
    whiptail --title "Runtime verification not reached" --msgbox \
      "Setup stopped before runtime verification. See the preceding terminal output for the error." 10 72 || true
  fi
  if (( status == 0 )); then
    break
  fi
  if ! whiptail --title "Installation incomplete" --defaultno --yesno \
    "Installation failed (exit $status). Your selections are saved. Retry now? Existing packages will be reused where possible." 12 78; then
    exit "$status"
  fi
done

if [[ "$SELECTED_TARGET" != termux ]]; then
  airplay_mode=""
  if airplay_mode="$(whiptail --title "Trending music" --menu \
    "Connect ORC to a MusicForge Airplay server now?" 13 76 3 \
    skip "Keep current settings" direct "Connect to an API URL" \
    tunnel "Set up a private SSH tunnel" 3>&1 1>&2 2>&3)"; then
    case "$airplay_mode" in
      direct)
        if url="$(whiptail --inputbox "MusicForge Airplay base URL" 10 76 \
          "https://airplay.example.com" 3>&1 1>&2 2>&3)"; then
          (cd "$PROJECT_DIR" && python3 -m scripts.installers.setup_musicforge_airplay "$url") || \
            echo "[!] Trending setup incomplete."
        fi
        ;;
      tunnel)
        if destination="$(whiptail --inputbox "VPS SSH destination (user@host)" 10 76 \
          "" 3>&1 1>&2 2>&3)" &&
           ssh_port="$(whiptail --inputbox "VPS SSH port" 10 76 "22" 3>&1 1>&2 2>&3)" &&
           api_port="$(whiptail --inputbox "VPS Airplay API port" 10 76 "8003" 3>&1 1>&2 2>&3)" &&
           login_key="$(whiptail --inputbox "One-time VPS login key path (optional)" 10 76 \
             "" 3>&1 1>&2 2>&3)"; then
          bash "$PROJECT_DIR/scripts/systemd/install_musicforge_airplay_tunnel.sh" \
            "$destination" "$ssh_port" "$api_port" "$login_key" || \
            echo "[!] Trending tunnel setup incomplete."
        fi
        ;;
    esac
  fi
fi

# Use the runtime secret parser; never source or print credential values.
MEDIA_PYTHON="${VENV_DIR:-$PROJECT_DIR/../.venv}/bin/python"
if [[ ! -x "$MEDIA_PYTHON" ]]; then MEDIA_PYTHON=python3; fi
has_media_secret() {
  (cd "$PROJECT_DIR" && "$MEDIA_PYTHON" -c 'import sys; from security.environment_variable_secret_manager import EnvironmentVariableSecretManager; sys.exit(not bool(EnvironmentVariableSecretManager().get_secret(sys.argv[1])))' "$1")
}
for provider in spotify youtube; do
  if [[ " $SELECTED_STREAMING " != *" $provider "* ]] && (( ! INSTALL_ALL_FEATURES )); then continue; fi
  secret=SPOTIFY_CLIENT_ID
  options=()
  if [[ "$provider" == youtube ]]; then secret=YOUTUBE_API_KEY; options+=(--prompt-youtube); fi
  if has_media_secret "$secret"; then
    echo "[*] $provider credentials already configured; skipping."
  elif whiptail --title "Media credentials" --yesno "Configure $provider credentials now? You can skip and configure them later." 12 78; then
    credential_platform=debian
    if [[ "${PREFIX:-}" == */com.termux/files/usr ]]; then credential_platform=termux; fi
    bash "$PROJECT_DIR/development/$credential_platform/install_secrets.sh" "${options[@]}" || echo "[!] $provider credential setup incomplete."
  fi
done

if [[ " $SELECTED_NAVIGATION " == *" navigation "* ]] || (( INSTALL_ALL_FEATURES )); then
  if whiptail --title "Home and Work addresses" --yesno \
    "Configure Home and Work destinations now?\n\nAddresses stay in your user configuration. You can skip this and configure them later." 12 78; then
    SETUP_PYTHON="python3"
    [[ -x "${VENV_DIR:-$PROJECT_DIR/../.venv}/bin/python" ]] && SETUP_PYTHON="${VENV_DIR:-$PROJECT_DIR/../.venv}/bin/python"
    (cd "$PROJECT_DIR" && "$SETUP_PYTHON" -m scripts.installers.setup_destinations) || \
      echo "[!] Address setup did not finish. Run it again as the ORC user."
  fi
fi

if [[ " $SELECTED_BLUETOOTH " == *" bluetooth "* ]] || (( INSTALL_ALL_FEATURES )); then
  if whiptail --title "Post-install configuration" --yesno "Configure a Bluetooth Serial Port Profile device now?" 10 72; then
    bash "$PROJECT_DIR/scripts/installers/setup_bluetooth_spp.sh"
  fi
fi
