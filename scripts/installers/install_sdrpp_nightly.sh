#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ORC_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SETUP_SCRIPT="$ORC_ROOT/development/debian/setup_sdrpp.sh"

[[ -x "$SETUP_SCRIPT" ]] || {
  echo "[!] SDR++ source-build helper was not found or is not executable:" >&2
  echo "    $SETUP_SCRIPT" >&2
  exit 1
}

if [[ ! -r /etc/os-release ]]; then
  echo "[!] /etc/os-release was not found; Debian/Ubuntu host expected." >&2
  exit 1
fi

# shellcheck disable=SC1091
. /etc/os-release
CODENAME="${VERSION_CODENAME:-unknown}"
ARCH="$(dpkg --print-architecture)"

echo "[*] Ubuntu/Debian codename: $CODENAME"
echo "[*] Architecture:           $ARCH"
echo "[*] SDR++ source ref:       ${SDRPP_REF:-master}"
echo

STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/openroadcode"
STATE_FILE="$STATE_DIR/sdrpp-build.sha256"

compute_build_fingerprint() {
  {
    printf 'SDRPP_REF=%s\n' "${SDRPP_REF:-master}"
    find "$ORC_ROOT/development/sdrpp/remote_control" \
         "$ORC_ROOT/development/sdrpp/telemetry" \
         -type f -print0 | sort -z | xargs -0 sha256sum
    sha256sum "$SETUP_SCRIPT"
  } | sha256sum | awk '{print $1}'
}

BUILD_FINGERPRINT="$(compute_build_fingerprint)"
INSTALLED_FINGERPRINT=""
[[ -f "$STATE_FILE" ]] && INSTALLED_FINGERPRINT="$(cat "$STATE_FILE")"

if [[ "${FORCE_SDRPP_REBUILD:-0}" != "1" ]] \
   && command -v sdrpp >/dev/null 2>&1 \
   && [[ "$INSTALLED_FINGERPRINT" == "$BUILD_FINGERPRINT" ]]; then
  echo "[+] OpenRoadCode SDR++ build is current; skipping rebuild."
else
  echo "[*] Building SDR++ from source with the OpenRoadCode modules"
  echo "    remote_control.so"
  echo "    telemetry.so"
  echo "    rigctl_server.so"
  echo

  # development/debian/setup_sdrpp.sh is the canonical Linux source-build path.
  "$SETUP_SCRIPT"

  mkdir -p "$STATE_DIR"
  printf '%s\n' "$BUILD_FINGERPRINT" > "$STATE_FILE"
fi

if command -v udevadm >/dev/null 2>&1; then
  if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
    SUDO=sudo
  else
    SUDO=
  fi

  echo "[*] Installing RTL-SDR udev rule..."
  $SUDO tee /etc/udev/rules.d/20-rtlsdr.rules >/dev/null <<'EOF'
SUBSYSTEM=="usb", ATTRS{idVendor}=="0bda", ATTRS{idProduct}=="2832", GROUP="plugdev", MODE="0660"
SUBSYSTEM=="usb", ATTRS{idVendor}=="0bda", ATTRS{idProduct}=="2838", GROUP="plugdev", MODE="0660"
SUBSYSTEM=="usb", ATTRS{idVendor}=="0bda", ATTRS{idProduct}=="2830", GROUP="plugdev", MODE="0660"
EOF
  $SUDO usermod -aG plugdev "$USER" || true
  $SUDO udevadm control --reload-rules
  $SUDO udevadm trigger || true
fi

if ! command -v sdrpp >/dev/null 2>&1; then
  echo "[!] Source build completed but sdrpp is not available in PATH." >&2
  exit 1
fi

echo
echo "[+] OpenRoadCode SDR++ source build installed."
echo "    launcher: $(command -v sdrpp)"
echo "    source:   ${SDRPP_SRC:-$HOME/SDRPlusPlus}"
echo "    ref:      ${SDRPP_REF:-master}"
echo
echo "Test SDR:"
echo "    rtl_test -t"
echo
echo "Launch SDR++ with the ORC modules:"
echo "    sdrpp --autostart"
echo
echo "[!] Replug the SDR dongle or log out/in if group permissions changed."
