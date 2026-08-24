#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

LIBRESPOT_VERSION="${LIBRESPOT_VERSION:-0.8.0}"
DEVICE_NAME="${LIBRESPOT_DEVICE_NAME:-CarUI}"
INSTALL_ROOT="${LIBRESPOT_INSTALL_ROOT:-$HOME/.local}"
CACHE_DIR="${LIBRESPOT_CACHE_DIR:-$HOME/.cache/openroadcode/librespot}"
SERVICE_DIR="${LIBRESPOT_SERVICE_DIR:-$HOME/.config/systemd/user}"
SERVICE_NAME="${LIBRESPOT_SERVICE_NAME:-openroadcode-librespot}"
DRY_RUN=0
SKIP_PACKAGES=0
SKIP_BUILD=0

usage() {
  cat <<EOF
Usage: $0 [options]

Install librespot as a user-level Spotify Connect receiver routed through
PipeWire's PulseAudio compatibility service.

Options:
  --device-name NAME  Spotify Connect device name (default: CarUI)
  --version VERSION   librespot crate version (default: $LIBRESPOT_VERSION)
  --skip-packages     Do not install Debian build/runtime packages
  --skip-build        Keep an existing librespot binary
  --dry-run           Print the installation plan without changing the host
  -h, --help          Show this help
EOF
}

while (( $# > 0 )); do
  case "$1" in
    --device-name)
      shift; (( $# > 0 )) || { echo "--device-name requires a value" >&2; exit 1; }
      DEVICE_NAME="$1"
      ;;
    --version)
      shift; (( $# > 0 )) || { echo "--version requires a value" >&2; exit 1; }
      LIBRESPOT_VERSION="$1"
      ;;
    --skip-packages) SKIP_PACKAGES=1 ;;
    --skip-build) SKIP_BUILD=1 ;;
    --dry-run) DRY_RUN=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 1 ;;
  esac
  shift
done

if [[ $EUID -eq 0 ]]; then
  echo "Run this installer as the desktop user, not with sudo." >&2
  echo "It invokes sudo only for system packages and installs the service under that user." >&2
  exit 1
fi
if [[ "$DEVICE_NAME" == *$'\n'* || "$DEVICE_NAME" == *$'\r'* || ! "$DEVICE_NAME" =~ ^[A-Za-z0-9._[:space:]-]+$ ]]; then
  echo "Device name contains unsupported characters: $DEVICE_NAME" >&2
  exit 1
fi

LIBRESPOT_BIN="$INSTALL_ROOT/bin/librespot"
SERVICE_FILE="$SERVICE_DIR/$SERVICE_NAME.service"

echo "[*] librespot version: $LIBRESPOT_VERSION"
echo "[*] Connect name:      $DEVICE_NAME"
echo "[*] Binary:           $LIBRESPOT_BIN"
echo "[*] Cache:            $CACHE_DIR"
echo "[*] User service:     $SERVICE_FILE"
echo "[*] Audio backend:    pulseaudio (PipeWire monitor-visible)"

if (( DRY_RUN )); then
  echo "[*] Dry run; no changes were made."
  exit 0
fi

if (( ! SKIP_PACKAGES )); then
  sudo apt-get update
  sudo apt-get install -y \
    avahi-daemon \
    build-essential \
    cargo \
    libavahi-client-dev \
    libpulse-dev \
    pkg-config
  sudo systemctl enable --now avahi-daemon.service
fi

if (( ! SKIP_BUILD )); then
  command -v cargo >/dev/null 2>&1 || {
    echo "cargo is unavailable; install it or omit --skip-packages." >&2
    exit 1
  }
  cargo install librespot \
    --version "$LIBRESPOT_VERSION" \
    --locked \
    --root "$INSTALL_ROOT" \
    --no-default-features \
    --features "rustls-tls-native-roots pulseaudio-backend with-avahi"
fi

if [[ ! -x "$LIBRESPOT_BIN" ]]; then
  echo "librespot binary not found after installation: $LIBRESPOT_BIN" >&2
  exit 1
fi
command -v systemctl >/dev/null 2>&1 || {
  echo "systemctl is required to install the user service." >&2
  exit 1
}

install -d -m 0700 "$CACHE_DIR"
install -d -m 0700 "$SERVICE_DIR"

temporary_service="$(mktemp "$SERVICE_DIR/.${SERVICE_NAME}.XXXXXX")"
trap 'rm -f "$temporary_service"' EXIT
cat > "$temporary_service" <<EOF
[Unit]
Description=OpenRoadCode Spotify Connect receiver
Wants=network-online.target pipewire-pulse.service
After=network-online.target pipewire-pulse.service

[Service]
Type=simple
Environment=PULSE_SERVER=unix:%t/pulse/native
ExecStart=$LIBRESPOT_BIN --name "$DEVICE_NAME" --device-type automobile --backend pulseaudio --bitrate 320 --cache $CACHE_DIR --enable-volume-normalisation --initial-volume 50
Restart=on-failure
RestartSec=3

[Install]
WantedBy=default.target
EOF
chmod 0600 "$temporary_service"
mv "$temporary_service" "$SERVICE_FILE"
trap - EXIT

systemctl --user daemon-reload
systemctl --user enable --now "$SERVICE_NAME.service"

echo
echo "[+] Spotify Connect receiver installed and started."
echo "    Select '$DEVICE_NAME' from Spotify's device picker."
echo "    Status: systemctl --user status $SERVICE_NAME.service"
echo "    Logs:   journalctl --user -u $SERVICE_NAME.service -f"
echo "    CarUI visualizer source: System Audio"
