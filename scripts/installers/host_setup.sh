#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$PROJECT_ROOT}"
VENV_DIR="${VENV_DIR:-$PROJECT_DIR/venv}"
export PROJECT_DIR VENV_DIR

FEATURES_FILE="$SCRIPT_DIR/installer_features.sh"
if [[ ! -f "$FEATURES_FILE" ]]; then
  echo "[!] Feature definitions not found: $FEATURES_FILE" >&2
  exit 1
fi
# shellcheck disable=SC1091
source "$FEATURES_FILE"

DISPLAY_NUM="${DISPLAY_NUM:-2}"
GEOMETRY="${GEOMETRY:-1280x720}"
DEPTH="${DEPTH:-24}"
GPS_DEVICE="${GPS_DEVICE:-/dev/ttyACM0}"

TARGET=""
FORCE_TARGET=0
SHOW_PLAN=0
SKIP_INSTALLS=0
RUN_SYSTEM_PACKAGES=1
RUN_PYTHON_ENV=1
RUN_VNC=""
RUN_GPSD_SERVICE=""
RUN_TELEMETRY_SERVICES=""
REQUESTED_FEATURES=()
USE_DEFAULT_FEATURES=1
INSTALL_ALL_FEATURES=0

usage() {
  cat <<EOF
Usage: $0 --target TARGET [options]

Targets:
  rpi4       Raspberry Pi 4 or Compute Module 4 runtime
  rpi5       Raspberry Pi 5, Pi 500, or Compute Module 5 runtime
  linux-dev  Debian/Ubuntu development workstation or VM

Options:
  --target TARGET         Required installation target
  --force-target          Continue without prompting when detection disagrees
  --show-plan             Print the resolved plan without changing the system
  --skip-installs         Skip packages, Python setup, and group changes
  --no-system-packages    Skip system package installation
  --no-python-env         Skip Python virtualenv/package setup
  --with-vnc              Enable VNC service setup
  --no-vnc                Disable VNC service setup
  --with-gpsd-service     Enable GPSD service setup
  --no-gpsd-service       Disable GPSD service setup
  --with-telemetry-services Enable broker/navigation/automotive services
  --no-telemetry-services Disable OpenRoadCode telemetry service setup
  --feature NAME          Add a feature bundle to the target profile
  --all-features          Install every feature compatible with the target
  --no-default-features   Start with no optional target-profile features
  -h, --help              Show this help
EOF
  echo
  get_feature_help
}

read_os_release_value() {
  local key="$1"
  local os_release_file="${OPENROAD_OS_RELEASE_FILE:-/etc/os-release}"
  local value=""
  if [[ -r "$os_release_file" ]]; then
    value="$(sed -n -E "s/^${key}=(.*)$/\1/p" "$os_release_file" | head -n 1 | sed -E 's/^"(.*)"$/\1/')"
  fi
  printf '%s\n' "$value"
}

detect_host_arch() {
  local arch="${OPENROAD_HOST_ARCH:-}"
  if [[ -z "$arch" ]] && command -v dpkg >/dev/null 2>&1; then
    arch="$(dpkg --print-architecture 2>/dev/null || true)"
  fi
  [[ -n "$arch" ]] || arch="$(uname -m 2>/dev/null || true)"
  case "$arch" in
    amd64|x86_64|x64) echo "amd64" ;;
    arm64|aarch64) echo "arm64" ;;
    armhf|armv7l|armv6l|armv8l) echo "armhf" ;;
    *) echo "$arch" ;;
  esac
}

detect_raspberry_pi_model() {
  local model_file="${OPENROAD_RPI_MODEL_FILE:-/proc/device-tree/model}"
  if [[ -r "$model_file" ]]; then
    tr -d '\0' < "$model_file"
  fi
  return 0
}

detect_system_target() {
  local model="$1"
  case "$model" in
    *"Raspberry Pi 4"*|*"Compute Module 4"*) echo "rpi4" ;;
    *"Raspberry Pi 5"*|*"Raspberry Pi 500"*|*"Compute Module 5"*) echo "rpi5" ;;
    *"Raspberry Pi"*|*"Compute Module"*) echo "unknown-rpi" ;;
    "")
      if [[ "${OPENROAD_HOST_SYSTEM:-$(uname -s 2>/dev/null || true)}" == "Linux" ]]; then echo "linux-dev"; else echo "unsupported"; fi
      ;;
    *) echo "unsupported" ;;
  esac
}

validate_distribution() {
  local distribution_id="$1" distribution_like="$2"
  case "$distribution_id" in debian|ubuntu|raspbian) return 0 ;; esac
  if [[ " $distribution_like " == *" debian "* || " $distribution_like " == *" ubuntu "* ]]; then
    echo "[!] Distribution '$distribution_id' is Debian-compatible but not officially verified."
    return 0
  fi
  echo "[!] Unsupported distribution: ${distribution_id:-unknown}" >&2
  echo "[!] OpenRoadCode installation currently requires Debian, Ubuntu, or Raspberry Pi OS." >&2
  exit 1
}

confirm_target_mismatch() {
  local requested="$1" detected="$2" model="$3"
  [[ "$requested" == "$detected" ]] && return 0
  echo >&2
  echo "[!] WARNING: The selected target does not match the detected system." >&2
  echo "    Requested target: $requested" >&2
  echo "    Detected target:  $detected" >&2
  [[ -z "$model" ]] || echo "    Detected model:   $model" >&2
  echo "    Continuing may install incompatible packages or services." >&2
  if (( SHOW_PLAN )); then echo "[!] Plan-only mode: reporting the mismatch without prompting." >&2; return 0; fi
  if (( FORCE_TARGET )); then echo "[!] Continuing because --force-target was supplied." >&2; return 0; fi
  if [[ ! -t 0 ]]; then
    echo "[!] Refusing a noninteractive mismatched install." >&2
    echo "[!] Re-run with --force-target only if this target is intentional." >&2
    exit 1
  fi
  local answer=""
  read -r -p "Continue with the $requested installation? [y/N] " answer
  case "$answer" in y|Y|yes|YES|Yes) ;; *) echo "[*] Installation cancelled."; exit 1 ;; esac
}

append_feature() {
  local feature="$1"
  [[ " ${FEATURES[*]} " == *" $feature "* ]] || FEATURES+=("$feature")
}

while (( $# > 0 )); do
  case "$1" in
    --target) shift; (( $# > 0 )) || { echo "[!] --target requires a value" >&2; exit 1; }; TARGET="$1" ;;
    --force-target) FORCE_TARGET=1 ;;
    --show-plan) SHOW_PLAN=1 ;;
    --skip-installs) SKIP_INSTALLS=1 ;;
    --no-system-packages) RUN_SYSTEM_PACKAGES=0 ;;
    --no-python-env) RUN_PYTHON_ENV=0 ;;
    --with-vnc) RUN_VNC=1 ;;
    --no-vnc) RUN_VNC=0 ;;
    --with-gpsd-service) RUN_GPSD_SERVICE=1 ;;
    --no-gpsd-service) RUN_GPSD_SERVICE=0 ;;
    --with-telemetry-services) RUN_TELEMETRY_SERVICES=1 ;;
    --no-telemetry-services) RUN_TELEMETRY_SERVICES=0 ;;
    --no-default-features) USE_DEFAULT_FEATURES=0 ;;
    --all-features) INSTALL_ALL_FEATURES=1 ;;
    --feature) option="$1"; shift; (( $# > 0 )) || { echo "[!] $option requires a value" >&2; exit 1; }; REQUESTED_FEATURES+=("$1") ;;
    -h|--help) usage; exit 0 ;;
    *) echo "[!] Unknown argument: $1" >&2; usage >&2; exit 1 ;;
  esac
  shift
done

[[ -n "$TARGET" ]] || { echo "[!] --target is required" >&2; usage >&2; exit 1; }
case "$TARGET" in rpi4|rpi5|linux-dev) ;; *) echo "[!] Unknown target: $TARGET" >&2; usage >&2; exit 1 ;; esac

HOST_ARCH="$(detect_host_arch)"
RPI_MODEL="$(detect_raspberry_pi_model)"
DETECTED_TARGET="$(detect_system_target "$RPI_MODEL")"
DISTRO_ID="$(read_os_release_value ID)"
DISTRO_LIKE="$(read_os_release_value ID_LIKE)"
validate_distribution "$DISTRO_ID" "$DISTRO_LIKE"
confirm_target_mismatch "$TARGET" "$DETECTED_TARGET" "$RPI_MODEL"

FEATURES=()
if (( INSTALL_ALL_FEATURES )); then mapfile -t FEATURES < <(get_all_features_for_target "$TARGET"); elif (( USE_DEFAULT_FEATURES )); then FEATURES=(base); fi
case "$TARGET" in
  rpi4) GPIO_BACKEND="RPi.GPIO"; append_feature raspberry-pi ;;
  rpi5) GPIO_BACKEND="rpi-lgpio"; append_feature raspberry-pi ;;
  linux-dev) GPIO_BACKEND="" ;;
esac
: "${RUN_VNC:=0}"
: "${RUN_GPSD_SERVICE:=0}"
: "${RUN_TELEMETRY_SERVICES:=0}"

for feature in "${REQUESTED_FEATURES[@]}"; do
  is_known_feature "$feature" || { echo "[!] Unknown feature: $feature" >&2; get_feature_help >&2; exit 1; }
  append_feature "$feature"
done
(( RUN_VNC )) && append_feature vnc
(( RUN_GPSD_SERVICE )) && append_feature gps

feature_index=0
while (( feature_index < ${#FEATURES[@]} )); do
  feature="${FEATURES[$feature_index]}"
  while read -r dependency; do [[ -z "$dependency" ]] || append_feature "$dependency"; done < <(get_feature_dependencies "$feature" | tr ' ' '\n')
  feature_index=$((feature_index + 1))
done
for feature in "${FEATURES[@]}"; do is_known_feature "$feature" || { echo "[!] Internal error: unknown resolved feature '$feature'" >&2; exit 1; }; done

export OPENROAD_INSTALL_TARGET="$TARGET"
export OPENROAD_RPI_GPIO_BACKEND="$GPIO_BACKEND"

echo "[*] Requested target:      $TARGET"
echo "[*] Detected target:       $DETECTED_TARGET"
echo "[*] Detected architecture: $HOST_ARCH"
echo "[*] Distribution:          ${DISTRO_ID:-unknown}"
[[ -z "$RPI_MODEL" ]] || echo "[*] Raspberry Pi model:    $RPI_MODEL"
[[ -z "$GPIO_BACKEND" ]] || echo "[*] GPIO backend:          $GPIO_BACKEND"
echo "[*] Features:              ${FEATURES[*]}"
echo "[*] VNC service setup:     $RUN_VNC"
echo "[*] GPSD service setup:    $RUN_GPSD_SERVICE"
echo "[*] Telemetry services:    $RUN_TELEMETRY_SERVICES"

if (( SHOW_PLAN )); then echo "[*] Plan only; no system changes were made."; exit 0; fi
if (( SKIP_INSTALLS )); then echo "[*] Skipping package, Python, and user-group changes per request."; fi
if (( RUN_SYSTEM_PACKAGES )) && (( ! SKIP_INSTALLS )); then bash "$PROJECT_DIR/scripts/installers/install_system_packages.sh" "${FEATURES[@]}"; fi
if (( RUN_PYTHON_ENV )) && (( ! SKIP_INSTALLS )); then bash "$PROJECT_DIR/scripts/installers/install_python_env.sh" "${FEATURES[@]}"; fi
if (( ! SKIP_INSTALLS )); then bash "$PROJECT_DIR/scripts/installers/configure_user_permissions.sh" "${FEATURES[@]}"; fi

if (( RUN_VNC )) || (( RUN_GPSD_SERVICE )) || (( RUN_TELEMETRY_SERVICES )); then
  service_args=()
  (( RUN_VNC )) && service_args+=(--vnc)
  (( RUN_GPSD_SERVICE )) && service_args+=(--gpsd --gps-device "$GPS_DEVICE")
  (( RUN_TELEMETRY_SERVICES )) && service_args+=(--telemetry)
  bash "$PROJECT_DIR/scripts/installers/install_services.sh" "${service_args[@]}"
fi

VERIFY_PYTHON="python3"
[[ -x "$VENV_DIR/bin/python" ]] && VERIFY_PYTHON="$VENV_DIR/bin/python"

if (( ! SKIP_INSTALLS )); then
  echo
  echo "[*] Verifying installed dependencies..."
  "$VERIFY_PYTHON" "$SCRIPT_DIR/verify_installation.py" "${FEATURES[@]}"
fi

echo
echo "[*] Verifying runtime health..."
runtime_args=("${FEATURES[@]}" --config "$PROJECT_DIR/config/runtime.toml")
(( RUN_TELEMETRY_SERVICES )) && runtime_args+=(--telemetry-services)
(( RUN_GPSD_SERVICE )) && runtime_args+=(--gpsd-service)
"$VERIFY_PYTHON" "$SCRIPT_DIR/verify_runtime.py" "${runtime_args[@]}"

echo
echo "[+] $TARGET setup complete."
echo "    Project dir: $PROJECT_DIR"
echo "    Arch:        $HOST_ARCH"
echo "    Venv:        $VENV_DIR"
echo
echo "[*] Activate Python venv with:"
echo "    source \"$VENV_DIR/bin/activate\""
