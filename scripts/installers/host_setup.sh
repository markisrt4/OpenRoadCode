#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$PROJECT_ROOT}"
VENV_DIR="${VENV_DIR:-$PROJECT_DIR/venv}"
export PROJECT_DIR VENV_DIR

DISPLAY_NUM="${DISPLAY_NUM:-2}"
GEOMETRY="${GEOMETRY:-1280x720}"
DEPTH="${DEPTH:-24}"
GPS_DEVICE="${GPS_DEVICE:-/dev/ttyACM0}"

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
    HOST_ARCH_LABEL="x86_64/amd64"
    HOST_ARCH_NOTE="Desktop or general Linux host detected."
    INSTALL_FLOW="desktop"
    ;;
  arm64)
    HOST_ARCH_LABEL="ARM64/aarch64"
    HOST_ARCH_NOTE="Raspberry Pi 64-bit or ARM64 host detected."
    INSTALL_FLOW="raspberry-pi"
    ;;
  armhf)
    HOST_ARCH_LABEL="ARM32/armhf"
    HOST_ARCH_NOTE="32-bit ARM host detected."
    INSTALL_FLOW="raspberry-pi"
    ;;
  *)
    HOST_ARCH_LABEL="$HOST_ARCH"
    HOST_ARCH_NOTE="Generic Linux host detected."
    INSTALL_FLOW="generic"
    ;;
esac

SKIP_INSTALLS=0
RUN_SYSTEM_PACKAGES=1
RUN_PYTHON_ENV=1
RUN_VNC=1
RUN_GPSD_SERVICE=1
RUN_SDRPP=0
RUN_RADIO=0
REQUESTED_FEATURES=()

while (( $# > 0 )); do
  case "$1" in
    --skip-installs)
      SKIP_INSTALLS=1
      ;;
    --no-system-packages)
      RUN_SYSTEM_PACKAGES=0
      ;;
    --no-python-env)
      RUN_PYTHON_ENV=0
      ;;
    --no-vnc)
      RUN_VNC=0
      ;;
    --no-gpsd-service)
      RUN_GPSD_SERVICE=0
      ;;
    --install-sdrpp)
      RUN_SDRPP=1
      ;;
    --install-radio)
      RUN_RADIO=1
      ;;
    --feature)
      shift
      if (( $# == 0 )); then
        echo "[!] --feature requires a value" >&2
        exit 1
      fi
      REQUESTED_FEATURES+=("$1")
      ;;
    -h|--help)
      echo "Usage: $0 [options]"
      echo "  --skip-installs        Skip apt and pip installs"
      echo "  --no-system-packages   Skip system package installation"
      echo "  --no-python-env        Skip Python virtualenv/package setup"
      echo "  --no-vnc               Skip VNC setup"
      echo "  --no-gpsd-service      Skip GPS systemd service setup"
      echo "  --install-sdrpp        Install SDR++ if available"
      echo "  --install-radio        Install or update the radio stack"
      echo "  --feature NAME         Add a feature bundle (base, core-ui, gps, radio, spotify, sdrpp)"
      exit 0
      ;;
    *)
      echo "[!] Unknown argument: $1" >&2
      echo "Usage: $0 [options]" >&2
      exit 1
      ;;
  esac
  shift
done

echo "[*] Detected host architecture: $HOST_ARCH_LABEL ($HOST_ARCH)"
echo "[*] Install flow: $INSTALL_FLOW"
echo "[*] $HOST_ARCH_NOTE"

if (( SKIP_INSTALLS )); then
  echo "[*] Skipping apt and pip installs per request."
fi

FEATURES=()
if (( ${#REQUESTED_FEATURES[@]} > 0 )); then
  FEATURES=("${REQUESTED_FEATURES[@]}")
else
  FEATURES=(base)
  if [[ "$HOST_ARCH" == "amd64" ]]; then
    FEATURES+=(core-ui)
  fi
  FEATURES+=(gps)
  FEATURES+=(streamlit)
  FEATURES+=(bluetooth)
  FEATURES+=(automotive)
  if (( RUN_SDRPP )); then
    FEATURES+=(sdrpp)
  fi
  if (( RUN_RADIO )); then
    FEATURES+=(radio)
  fi
fi

if (( RUN_SYSTEM_PACKAGES )) && (( ! SKIP_INSTALLS )); then
  bash "$PROJECT_DIR/scripts/installers/install_system_packages.sh" "${FEATURES[@]}"
fi

if (( RUN_PYTHON_ENV )) && (( ! SKIP_INSTALLS )); then
  bash "$PROJECT_DIR/scripts/installers/install_python_env.sh" "${FEATURES[@]}"
fi

if (( RUN_SDRPP )); then
  echo "[*] Installing SDR++ if available..."
  if dpkg -s sdrpp >/dev/null 2>&1; then
    echo "[*] Already installed: sdrpp"
  elif apt-cache show sdrpp >/dev/null 2>&1; then
    sudo apt install -y --no-install-recommends sdrpp
  else
    echo "[!] Package not available, skipping: sdrpp"
  fi
fi

if (( RUN_RADIO )); then
  echo "[*] Running radio stack installer..."
  bash "$PROJECT_DIR/scripts/installers/install_radio.sh"
fi

if (( RUN_VNC )) || (( RUN_GPSD_SERVICE )); then
  bash "$PROJECT_DIR/scripts/installers/install_services.sh" "$RUN_VNC" "$RUN_GPSD_SERVICE"
fi

echo
echo "[+] $HOST_ARCH_NOTE setup complete."
echo "    Project dir: $PROJECT_DIR"
echo "    Arch:        $HOST_ARCH_LABEL"
echo "    Venv:        $VENV_DIR"
echo
echo "[*] Activate Python venv with:"
echo "    source \"$VENV_DIR/bin/activate\""
