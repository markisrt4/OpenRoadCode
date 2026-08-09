#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$PROJECT_ROOT}"

show_help() {
  cat <<'EOF'
Usage: install_radio.sh [options]

Install or update the radio stack for SDR/RTL-SDR support.

Options:
  -h, --help    Show this help text
EOF
}

case "${1:-}" in
  -h|--help)
    show_help
    exit 0
    ;;
  "")
    ;;
  *)
    echo "[!] Unknown argument: $1" >&2
    show_help >&2
    exit 1
    ;;
esac

detect_host_arch() {
  local arch=""

  if command -v dpkg >/dev/null 2>&1; then
    arch="$(dpkg --print-architecture 2>/dev/null || true)"
  fi

  if [[ -z "$arch" ]]; then
    arch="$(uname -m 2>/dev/null || true)"
  fi

  case "$arch" in
    amd64|x86_64|x64)
      echo "amd64"
      ;;
    arm64|aarch64)
      echo "arm64"
      ;;
    armhf|armv7l|armv6l|armv8l)
      echo "armhf"
      ;;
    *)
      echo "$arch"
      ;;
  esac
}

HOST_ARCH="$(detect_host_arch)"
case "$HOST_ARCH" in
  amd64)
    echo "[*] Detected x86_64/amd64 host; preparing desktop radio support."
    ;;
  arm64|armhf)
    echo "[*] Detected ARM host; preparing Raspberry Pi radio support."
    ;;
  *)
    echo "[*] Detected host architecture: $HOST_ARCH"
    ;;
esac

echo "[*] Updating apt package lists..."
sudo apt update

echo "[*] Installing RTL-SDR support packages..."
radio_packages=(
  rtl-sdr
  soapysdr-tools
  soapysdr-module-rtlsdr
  x11-apps
  curl
  ca-certificates
  jq
)

available_packages=()
for pkg in "${radio_packages[@]}"; do
  if dpkg -s "$pkg" >/dev/null 2>&1; then
    echo "[*] Already installed: $pkg"
    continue
  fi

  if apt-cache show "$pkg" >/dev/null 2>&1; then
    available_packages+=("$pkg")
  else
    echo "[!] Package not available, skipping: $pkg"
  fi
done

if (( ${#available_packages[@]} > 0 )); then
  echo "[*] Installing: ${available_packages[*]}"
  sudo apt install -y --no-install-recommends "${available_packages[@]}"
fi

echo "[*] Installing or updating SDR++ support..."
if dpkg -s sdrpp >/dev/null 2>&1; then
  echo "[*] Already installed: sdrpp"
elif apt-cache show sdrpp >/dev/null 2>&1; then
  sudo apt install -y --no-install-recommends sdrpp
else
  echo "[!] sdrpp package not available in apt; falling back to the nightly installer."
  bash "$PROJECT_DIR/scripts/installers/install_sdrpp_nightly.sh"
fi

echo "[*] Writing RTL-SDR udev rules..."
sudo tee /etc/udev/rules.d/20-rtlsdr.rules >/dev/null <<'EOF'
SUBSYSTEM=="usb", ATTRS{idVendor}=="0bda", ATTRS{idProduct}=="2832", GROUP="plugdev", MODE="0660"
SUBSYSTEM=="usb", ATTRS{idVendor}=="0bda", ATTRS{idProduct}=="2838", GROUP="plugdev", MODE="0660"
SUBSYSTEM=="usb", ATTRS{idVendor}=="0bda", ATTRS{idProduct}=="2830", GROUP="plugdev", MODE="0660"
EOF

sudo usermod -aG plugdev "$USER" || true
sudo udevadm control --reload-rules >/dev/null 2>&1 || true
sudo udevadm trigger >/dev/null 2>&1 || true

echo
echo "[+] Radio stack update complete."
echo "[*] Test RTL-SDR with: rtl_test -t"
echo "[*] Launch SDR++ with: sdrpp"
