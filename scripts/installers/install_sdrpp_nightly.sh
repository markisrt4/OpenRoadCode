#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

REPO="hydrasdr/SDRPlusPlus"
CODENAME="$(. /etc/os-release && echo "${VERSION_CODENAME}")"
ARCH="$(dpkg --print-architecture)"

echo "[*] Ubuntu/Debian codename: $CODENAME"
echo "[*] Architecture:           $ARCH"

case "$CODENAME" in
  noble|jammy|focal) DISTRO=ubuntu ;;
  trixie|bookworm|bullseye|sid) DISTRO=debian ;;
  *) echo "[!] Unsupported codename: $CODENAME" >&2; exit 1 ;;
esac

TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

sudo apt update
sudo apt install -y curl ca-certificates jq rtl-sdr soapysdr-tools soapysdr-module-rtlsdr x11-apps

API_URL="https://api.github.com/repos/${REPO}/releases/tags/nightly"
RELEASE_JSON="$TMPDIR/release.json"
curl -fsSL "$API_URL" -o "$RELEASE_JSON"

asset_url() {
  jq -r --arg name "$1" '.assets[] | select(.name == $name) | .browser_download_url' "$RELEASE_JSON" | head -n1
}

ASSET_NAME="sdrpp_${DISTRO}_${CODENAME}_${ARCH}.deb"
DEB_URL="$(asset_url "$ASSET_NAME")"

# Trixie is not currently an upstream packaging target. Try the Bookworm
# build only after inspecting its dependencies against this machine.
if [[ -z "$DEB_URL" && "$CODENAME" == trixie ]]; then
  ASSET_NAME="sdrpp_debian_bookworm_${ARCH}.deb"
  DEB_URL="$(asset_url "$ASSET_NAME")"
  echo "[*] No native Trixie package; inspecting the Bookworm build."
fi

if [[ -z "$DEB_URL" ]]; then
  echo "[!] No matching nightly package for $CODENAME/$ARCH." >&2
  jq -r '.assets[].name | select(endswith(".deb"))' "$RELEASE_JSON" >&2
  exit 1
fi

DEB_FILE="$TMPDIR/$ASSET_NAME"
echo "[*] Downloading $ASSET_NAME"
curl -fL --retry 3 -o "$DEB_FILE" "$DEB_URL"

PACKAGE_ARCH="$(dpkg-deb -f "$DEB_FILE" Architecture)"
if [[ "$PACKAGE_ARCH" != "$ARCH" && "$PACKAGE_ARCH" != all ]]; then
  echo "[!] Package architecture mismatch: $PACKAGE_ARCH" >&2
  exit 1
fi

echo "[*] Package dependencies:"
dpkg-deb -f "$DEB_FILE" Depends || true
echo

# APT's simulator resolves dependencies using the host's configured repos.
# Never add an older Debian repository or force dependency installation.
SIMULATION="$TMPDIR/apt-simulation.txt"
if ! apt-get -s install "$DEB_FILE" >"$SIMULATION" 2>&1; then
  cat "$SIMULATION" >&2
  echo "[!] Package dependencies are not satisfiable on this host." >&2
  echo "[*] Use a native source build instead of mixing Debian releases." >&2
  exit 1
fi
cat "$SIMULATION"
if grep -Eq '^Remv ' "$SIMULATION"; then
  echo "[!] APT would remove installed packages. Refusing installation." >&2
  exit 1
fi

sudo apt install -y "$DEB_FILE"

if [[ ! -e /usr/bin/sdrpp ]] && ! command -v sdrpp >/dev/null 2>&1; then
  echo "[!] Installation completed but sdrpp was not found in PATH." >&2
  exit 1
fi

if command -v udevadm >/dev/null 2>&1; then
  echo "[*] Installing RTL-SDR udev rule..."
  sudo tee /etc/udev/rules.d/20-rtlsdr.rules >/dev/null <<'EOF'
SUBSYSTEM=="usb", ATTRS{idVendor}=="0bda", ATTRS{idProduct}=="2832", GROUP="plugdev", MODE="0660"
SUBSYSTEM=="usb", ATTRS{idVendor}=="0bda", ATTRS{idProduct}=="2838", GROUP="plugdev", MODE="0660"
SUBSYSTEM=="usb", ATTRS{idVendor}=="0bda", ATTRS{idProduct}=="2830", GROUP="plugdev", MODE="0660"
EOF
  sudo usermod -aG plugdev "$USER" || true
  sudo udevadm control --reload-rules
  sudo udevadm trigger || true
fi

echo
 echo "[+] SDR++ installed."
echo "Test SDR: rtl_test -t"
echo "Launch SDR++: sdrpp"
echo "[!] Replug the SDR dongle or log out/in if permissions are weird."
