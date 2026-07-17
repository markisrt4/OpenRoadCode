#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$PROJECT_ROOT}"
FEATURES_FILE="$SCRIPT_DIR/installer_features.sh"

if [[ ! -f "$FEATURES_FILE" ]]; then
  echo "[!] Feature definitions not found: $FEATURES_FILE" >&2
  exit 1
fi
# shellcheck disable=SC1091
source "$FEATURES_FILE"

if (( $# > 0 )); then
  FEATURES=("$@")
else
  mapfile -t FEATURES < <(get_feature_defaults)
fi

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
    echo "[*] Detected x86_64/amd64 host; using desktop-oriented package flow."
    ;;
  arm64|armhf)
    echo "[*] Detected ARM host; using Raspberry Pi-friendly package flow."
    ;;
  *)
    echo "[*] Detected host architecture: $HOST_ARCH"
    ;;
esac

echo "[*] Updating apt..."
sudo apt update

echo "[*] Installing feature-based packages..."
base_packages=()
for feature in "${FEATURES[@]}"; do
  while read -r pkg; do
    [[ -z "$pkg" ]] && continue
    base_packages+=("$pkg")
  done < <(get_feature_packages "$feature")
done

# Deduplicate while preserving order
unique_packages=()
for pkg in "${base_packages[@]}"; do
  if [[ " ${unique_packages[*]} " != *" $pkg "* ]]; then
    unique_packages+=("$pkg")
  fi
done

available_packages=()
for pkg in "${unique_packages[@]}"; do
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

if [[ " ${FEATURES[*]} " == *" core-ui "* ]]; then
  echo "[*] Installing Chromium..."
  if dpkg -s chromium >/dev/null 2>&1; then
    echo "[*] Already installed: chromium"
  elif dpkg -s chromium-browser >/dev/null 2>&1; then
    echo "[*] Already installed: chromium-browser"
  elif apt-cache show chromium >/dev/null 2>&1; then
    echo "[*] Installing Chromium browser: chromium"
    sudo apt install -y --no-install-recommends chromium
  elif apt-cache show chromium-browser >/dev/null 2>&1; then
    echo "[*] Installing Chromium browser: chromium-browser"
    sudo apt install -y --no-install-recommends chromium-browser
  else
    echo "[!] No available Chromium package found."
  fi
fi

if [[ " ${FEATURES[*]} " == *" sdrpp "* ]]; then
  echo "[*] Installing SDR++ if available..."
  if dpkg -s sdrpp >/dev/null 2>&1; then
    echo "[*] Already installed: sdrpp"
  elif apt-cache show sdrpp >/dev/null 2>&1; then
    sudo apt install -y --no-install-recommends sdrpp
  else
    echo "[!] Package not available, skipping: sdrpp"
  fi
fi
