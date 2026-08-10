#!/usr/bin/env bash
set -euo pipefail

# Capabilities are intentionally independent from installation targets.
# Targets describe the host platform; features describe optional software and
# hardware support installed on that platform.

get_known_features() {
  cat <<'EOF'
base
desktop-ui
browser
vnc
input
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
    rpi4|rpi5)
      get_known_features
      ;;
    linux-dev)
      cat <<'EOF'
base
desktop-ui
browser
vnc
input
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
    *)
      return 1
      ;;
  esac
}

is_known_feature() {
  local requested="$1"
  local feature
  while read -r feature; do
    [[ "$requested" == "$feature" ]] && return 0
  done < <(get_known_features)
  return 1
}

get_feature_dependencies() {
  local feature="$1"
  case "$feature" in
    vnc) echo "desktop-ui" ;;
    sdrpp) echo "rtl-sdr desktop-ui" ;;
    adsb) echo "rtl-sdr" ;;
    *) echo "" ;;
  esac
}

get_feature_packages() {
  local feature="$1"
  case "$feature" in
    base)
      echo "git curl wget ca-certificates python3 python3-venv python3-pip"
      ;;
    desktop-ui)
      echo "python3-tk dbus-x11 xauth xterm x11-apps wmctrl openbox xfce4 xfce4-goodies"
      ;;
    browser)
      echo ""
      ;;
    vnc)
      echo "tigervnc-standalone-server tigervnc-common"
      ;;
    input)
      echo ""
      ;;
    gps)
      echo "gpsd gpsd-clients python3-gps"
      ;;
    rtl-sdr)
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
    imu|environmental|raspberry-pi)
      echo "i2c-tools"
      ;;
    spotify)
      case "${OPENROAD_INSTALL_TARGET:-linux-dev}" in
        rpi4) echo "wireplumber pipewire-pulse alsa-utils" ;;
        rpi5) echo "wireplumber pipewire-pulse alsa-utils usbutils" ;;
        linux-dev) echo "pulseaudio-utils" ;;
        *) echo "" ;;
      esac
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
      printf '%s\n' requests tomli
      ;;
    desktop-ui)
      printf '%s\n' Pillow
      ;;
    browser|vnc|adsb|spotify|sdrpp)
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
    imu|environmental)
      echo ""
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
  base          Portable command-line runtime and Python environment
  desktop-ui    Tk, X11, Openbox, and XFCE desktop support
  browser       Chromium browser support
  vnc           TigerVNC server support (includes desktop-ui)
  input         Linux input/evdev support
  gps           GPSD and Python GPS/navigation support
  rtl-sdr       RTL-SDR device and SoapySDR support
  streamlit     Streamlit dashboard support
  adsb          readsb ADS-B support (includes rtl-sdr)
  bluetooth     Bluetooth system and Python support
  automotive    Serial and CAN-bus support
  imu           Generic I2C inertial-sensor tooling
  environmental Generic I2C environmental-sensor tooling
  spotify       Spotify integration extras
  sdrpp         SDR++ support (includes RTL-SDR and desktop-ui)
  raspberry-pi  Raspberry Pi GPIO, I2C, Blinka, and Seesaw support
EOF
}
