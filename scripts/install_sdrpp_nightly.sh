#!/usr/bin/env bash
set -euo pipefail

REPO="hydrasdr/SDRPlusPlus"

CODENAME="$(. /etc/os-release && echo "${VERSION_CODENAME}")"
ARCH="$(dpkg --print-architecture)"

echo "[*] Ubuntu/Debian codename: $CODENAME"
echo "[*] Architecture:           $ARCH"

case "$CODENAME" in
  noble|jammy|focal)
    ASSET_NAME="sdrpp_ubuntu_${CODENAME}_${ARCH}.deb"
    ;;
  bookworm|bullseye|sid)
    ASSET_NAME="sdrpp_debian_${CODENAME}_${ARCH}.deb"
    ;;
  *)
    echo "[!] Unsupported codename: $CODENAME"
    exit 1
    ;;
esac

echo "[*] Looking for asset:"
echo "    $ASSET_NAME"

sudo apt update
sudo apt install -y curl ca-certificates jq rtl-sdr soapysdr-tools soapysdr-module-rtlsdr x11-apps

API_URL="https://api.github.com/repos/${REPO}/releases/latest"

DEB_URL="$(
  curl -fsSL "$API_URL" |
    jq -r --arg name "$ASSET_NAME" '
      .assets[]
      | select(.name == $name)
      | .browser_download_url
    ' | head -n1
)"

if [[ -z "$DEB_URL" || "$DEB_URL" == "null" ]]; then
  echo "[!] Could not find matching asset."
  echo "[*] Available .deb assets:"
  curl -fsSL "$API_URL" |
    jq -r '.assets[].name' |
    grep '\.deb$' || true
  exit 1
fi

TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

DEB_FILE="$TMPDIR/$ASSET_NAME"

echo "[*] Downloading:"
echo "    $DEB_URL"

curl -L --fail -o "$DEB_FILE" "$DEB_URL"

echo "[*] Installing SDR++..."
sudo apt install -y "$DEB_FILE"

echo "[*] Installing RTL-SDR udev rule..."
sudo tee /etc/udev/rules.d/20-rtlsdr.rules >/dev/null <<'EOF'
SUBSYSTEM=="usb", ATTRS{idVendor}=="0bda", ATTRS{idProduct}=="2832", GROUP="plugdev", MODE="0666"
SUBSYSTEM=="usb", ATTRS{idVendor}=="0bda", ATTRS{idProduct}=="2838", GROUP="plugdev", MODE="0666"
SUBSYSTEM=="usb", ATTRS{idVendor}=="0bda", ATTRS{idProduct}=="2830", GROUP="plugdev", MODE="0666"
EOF

sudo usermod -aG plugdev "$USER" || true
sudo udevadm control --reload-rules
sudo udevadm trigger || true

echo
echo "[+] SDR++ installed."
echo
echo "Test SDR:"
echo "    rtl_test -t"
echo
echo "Launch SDR++ on VNC display :2:"
echo "    DISPLAY=:2 sdrpp &"
echo
echo "[!] Replug the SDR dongle or log out/in if permissions are weird."