#!/usr/bin/env bash
set -euo pipefail

# Feature definitions for the OpenRoadCode installer.
# Each feature can be enabled or disabled independently and maps to
# a named set of system packages, Python packages, and optional scripts.

get_feature_defaults() {
  cat <<'EOF'
base
core-ui
gps
radio
streamlit
adsb
bluetooth
automotive
spotify
sdrpp
EOF
}

get_feature_packages() {
  local feature="$1"
  case "$feature" in
    base)
      echo "git curl wget ca-certificates lighttpd bluez python3 python3-venv python3-tk python3-pip dbus-x11 xauth xterm x11-apps wmctrl openbox xfce4 xfce4-goodies tigervnc-standalone-server tigervnc-common rtl-sdr gpsd gpsd-clients python3-gps i2c-tools"
      ;;
    core-ui)
      echo "chromium"
      ;;
    gps)
      echo "gpsd gpsd-clients python3-gps"
      ;;
    radio)
      echo "rtl-sdr soapysdr-tools soapysdr-module-rtlsdr"
      ;;
    streamlit)
      echo ""
      ;;
    adsb)
      echo "readsb"
      ;;
    bluetooth)
      echo "bluez libbluetooth-dev python3-bluez"
      ;;
    automotive)
      echo "python3-serial libserial-dev can-utils"
      ;;
    spotify)
      echo ""
      ;;
    sdrpp)
      echo "sdrpp"
      ;;
    *)
      echo ""
      ;;
  esac
}

get_feature_python_packages() {
  local feature="$1"
  case "$feature" in
    base)
      printf '%s
' \
        streamlit \
        requests \
        geocoder \
        streamlit-autorefresh \
        gps \
        gpsd-py3 \
        pyserial \
        bleak \
        evdev \
        RPi.GPIO \
        adafruit-blinka \
        adafruit-circuitpython-seesaw \
        Pillow
      ;;
    core-ui)
      echo ""
      ;;
    gps)
      printf '%s
' \
        gps \
        gpsd-py3
      ;;
    radio)
      printf '%s
' \
        pyserial \
        bleak \
        evdev
      ;;
    streamlit)
      printf '%s
' \
        streamlit \
        streamlit-autorefresh
      ;;
    adsb)
      echo ""
      ;;
    bluetooth)
      printf '%s
' \
        bleak
      ;;
    automotive)
      printf '%s
' \
        pyserial
      ;;
    spotify)
      echo ""
      ;;
    sdrpp)
      echo ""
      ;;
    *)
      echo ""
      ;;
  esac
}

get_feature_help() {
  cat <<'EOF'
Available features:
  base        Core system and Python dependencies
  core-ui     Browser/UI support packages
  gps         GPS daemon and Python GPS support
  radio       RTL-SDR and radio-related packages
  streamlit   Streamlit dashboard support
  adsb        ADS-B/readsb support packages
  bluetooth   Bluetooth support packages
  automotive  Automotive/OBD-related support
  spotify     Spotify integration extras
  sdrpp       SDR++ package support
EOF
}
