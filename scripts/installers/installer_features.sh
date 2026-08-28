#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

# Capabilities are intentionally independent from installation targets.
# Targets describe the host platform; features describe optional software and
# hardware support installed on that platform.

get_known_features() {
  cat <<'EOF'
base
desktop-ui
web-ui
browser
vnc
input
audio
gps
rtl-sdr
streamlit
adsb
bluetooth
automotive
imu
environmental
spotify
sdrpp
raspberry-pi
EOF
}

get_all_features_for_target() {
  local target="$1"
  case "$target" in
    rpi4|rpi5) get_known_features ;;
    linux-dev)
      cat <<'EOF'
base
desktop-ui
web-ui
browser
vnc
input
audio
gps
rtl-sdr
streamlit
adsb
bluetooth
automotive
imu
environmental
spotify
sdrpp
EOF
      ;;
    *) return 1 ;;
  esac
}

is_known_feature() {
  local requested="$1" feature
  while read -r feature; do
    [[ "$requested" == "$feature" ]] && return 0
  done < <(get_known_features)
  return 1
}

get_feature_dependencies() {
  local feature="$1"
  case "$feature" in
    vnc) echo "desktop-ui" ;;
    spotify) echo "audio" ;;
    sdrpp) echo "rtl-sdr desktop-ui audio" ;;
    adsb) echo "rtl-sdr" ;;
    *) echo "" ;;
  esac
}

get_feature_packages() {
  local feature="$1"
  case "$feature" in
    base)
      echo "git curl wget ca-certificates sudo procps python3 python3-venv python3-pip"
      ;;
    desktop-ui)
      echo "python3-tk dbus-x11 xauth xterm x11-apps x11-utils wmctrl openbox xfce4 xfce4-goodies"
      ;;
    web-ui|browser|input|streamlit)
      echo ""
      ;;
    vnc)
      echo "tigervnc-standalone-server tigervnc-common"
      ;;
    audio)
      case "${OPENROAD_INSTALL_TARGET:-linux-dev}" in
        rpi4|rpi5) echo "wireplumber pipewire-pulse pipewire-bin pulseaudio-utils alsa-utils python3-numpy" ;;
        linux-dev) echo "pipewire-bin pulseaudio-utils python3-numpy" ;;
        *) echo "" ;;
      esac
      ;;
    gps)
      echo "gpsd gpsd-clients python3-gps"
      ;;
    rtl-sdr)
      echo "rtl-sdr soapysdr-tools soapysdr-module-rtlsdr"
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
    imu|environmental|raspberry-pi)
      echo "i2c-tools"
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
      printf '%s\n' requests tomli pyzmq
      ;;
    desktop-ui)
      printf '%s\n' Pillow
      ;;
    web-ui)
      printf '%s\n' Flask
      ;;
    browser|vnc|adsb|audio|spotify|sdrpp)
      echo ""
      ;;
    input)
      printf '%s\n' evdev
      ;;
    gps)
      printf '%s\n' gpsd-py3 geocoder
      ;;
    rtl-sdr)
      echo ""
      ;;
    streamlit)
      printf '%s\n' streamlit streamlit-autorefresh
      ;;
    bluetooth)
      printf '%s\n' bleak
      ;;
    automotive)
      printf '%s\n' pyserial
      ;;
    imu)
      printf '%s\n' adafruit-blinka adafruit-circuitpython-mpu6050
      ;;
    environmental)
      printf '%s\n' adafruit-blinka adafruit-circuitpython-bmp3xx
      ;;
    raspberry-pi)
      printf '%s\n' \
        raspberry-pi-gpio-backend \
        adafruit-blinka \
        adafruit-circuitpython-seesaw
      ;;
    *)
      echo ""
      ;;
  esac
}

get_feature_help() {
  cat <<'EOF'
Available features:
  base          Portable command-line runtime, ZeroMQ messaging, and Python environment
  desktop-ui    Tk, X11, Openbox, and XFCE desktop support
  web-ui        Flask-based OpenRoadCode browser frontend
  browser       Chromium browser support
  vnc           TigerVNC server support (includes desktop-ui)
  input         Linux input/evdev support
  audio         PipeWire/PulseAudio control, capture, and native music analysis
  gps           GPSD and Python GPS/navigation support
  rtl-sdr       RTL-SDR device and SoapySDR support
  streamlit     Streamlit dashboard support
  adsb          readsb + tar1090 ADS-B support (includes rtl-sdr)
  bluetooth     Bluetooth system and Python support
  automotive    Serial and CAN-bus support
  imu           MPU-6050 and Adafruit Blinka I2C support
  environmental BMP3XX and Adafruit Blinka I2C support
  spotify       Spotify integration extras (includes audio)
  sdrpp         SDR++ support (includes RTL-SDR, desktop-ui, and audio)
  raspberry-pi  Raspberry Pi GPIO, I2C, Blinka, and Seesaw support
EOF
}
