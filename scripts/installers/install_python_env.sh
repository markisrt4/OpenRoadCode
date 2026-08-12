#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$PROJECT_ROOT}"
VENV_DIR="${VENV_DIR:-$PROJECT_DIR/venv}"
FEATURES_FILE="$SCRIPT_DIR/installer_features.sh"

if [[ ! -f "$FEATURES_FILE" ]]; then
  echo "[!] Feature definitions not found: $FEATURES_FILE" >&2
  exit 1
fi
# shellcheck disable=SC1091
source "$FEATURES_FILE"

detect_raspberry_pi_model() {
  local model_file="${OPENROAD_RPI_MODEL_FILE:-/proc/device-tree/model}"

  if [[ -r "$model_file" ]]; then
    tr -d '\0' < "$model_file"
  fi
}

select_raspberry_pi_gpio_backend() {
  local target="$1"
  local model="$2"

  if [[ -n "${OPENROAD_RPI_GPIO_BACKEND:-}" ]]; then
    echo "$OPENROAD_RPI_GPIO_BACKEND"
    return
  fi

  case "$target" in
    rpi5)
      echo "rpi-lgpio"
      ;;
    rpi4)
      echo "RPi.GPIO"
      ;;
    *)
      case "$model" in
        *"Raspberry Pi 5"*|*"Raspberry Pi 500"*|*"Compute Module 5"*)
          echo "rpi-lgpio"
          ;;
        *)
          echo "RPi.GPIO"
          ;;
      esac
      ;;
  esac
}

if (( $# > 0 )); then
  FEATURES=("$@")
else
  FEATURES=(base)
fi

for feature in "${FEATURES[@]}"; do
  if ! is_known_feature "$feature"; then
    echo "[!] Unknown feature: $feature" >&2
    exit 1
  fi
done

echo "[*] Creating Python virtual environment..."
python3 -m venv --system-site-packages "$VENV_DIR"

echo "[*] Installing Python packages..."
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

python -m pip install --upgrade pip wheel setuptools

if [[ " ${FEATURES[*]} " == *" gps "* ]]; then
  gps_location="$(
    python -m pip show gps 2>/dev/null \
      | awk -F': ' '$1 == "Location" { print $2; exit }'
  )"
  if [[ -n "$gps_location" && "$gps_location" == "$VIRTUAL_ENV"/* ]]; then
    echo "[*] Removing incompatible PyPI gps package; using python3-gps instead..."
    python -m pip uninstall -y gps
  fi
fi

python_packages=()
rpi_model="$(detect_raspberry_pi_model)"
rpi_gpio_backend="$(
  select_raspberry_pi_gpio_backend \
    "${OPENROAD_INSTALL_TARGET:-}" \
    "$rpi_model"
)"

if [[ " ${FEATURES[*]} " == *" raspberry-pi "* ]]; then
  echo "[*] Raspberry Pi install target: ${OPENROAD_INSTALL_TARGET:-auto-detected}"
  if [[ -n "$rpi_model" ]]; then
    echo "[*] Detected Raspberry Pi model: $rpi_model"
  fi
  echo "[*] Selected GPIO backend: $rpi_gpio_backend"
fi

for feature in "${FEATURES[@]}"; do
  while read -r pkg; do
    [[ -z "$pkg" ]] && continue

    if [[ "$pkg" == "raspberry-pi-gpio-backend" ]]; then
      pkg="$rpi_gpio_backend"
    fi

    python_packages+=("$pkg")
  done < <(get_feature_python_packages "$feature")
done

unique_packages=()
for pkg in "${python_packages[@]}"; do
  if [[ " ${unique_packages[*]} " != *" $pkg "* ]]; then
    unique_packages+=("$pkg")
  fi
done

if [[ " ${unique_packages[*]} " == *" $rpi_gpio_backend "* ]]; then
  if [[ "$rpi_gpio_backend" == "rpi-lgpio" ]]; then
    conflicting_gpio_backend="RPi.GPIO"
  else
    conflicting_gpio_backend="rpi-lgpio"
  fi

  if python -m pip show "$conflicting_gpio_backend" >/dev/null 2>&1; then
    echo "[*] Removing conflicting GPIO backend: $conflicting_gpio_backend"
    python -m pip uninstall -y "$conflicting_gpio_backend"
  fi
fi

missing_python_packages=()
for pkg in "${unique_packages[@]}"; do
  if python -m pip show "$pkg" >/dev/null 2>&1; then
    echo "[*] Already installed in venv: $pkg"
  else
    missing_python_packages+=("$pkg")
  fi
done

if (( ${#missing_python_packages[@]} > 0 )); then
  echo "[*] Installing missing Python packages: ${missing_python_packages[*]}"
  python -m pip install --disable-pip-version-check "${missing_python_packages[@]}"
else
  echo "[*] All requested Python packages are already installed in the virtual environment."
fi

deactivate
