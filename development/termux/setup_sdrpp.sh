#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

[[ "${PREFIX:-}" == /data/data/com.termux/files/usr* ]] || {
  echo "This setup script must run inside Termux." >&2
  exit 2
}

SDRPP_REF="${SDRPP_REF:-master}"
BUILD_JOBS="${BUILD_JOBS:-4}"

command -v pkg >/dev/null 2>&1 || {
  echo "Termux pkg command was not found." >&2
  exit 1
}

echo "[*] Installing Termux proot support"
pkg install -y proot-distro git

if proot-distro list | grep -Eq '(^|[[:space:]])debian([[:space:]]|$)'; then
  echo "[*] Debian proot is already installed"
else
  echo "[*] Installing Debian proot"
  proot-distro install debian
fi

echo "[*] Installing SDR++ dependencies and building inside Debian"
proot-distro login debian --shared-tmp -- env \
  SDRPP_REF="$SDRPP_REF" \
  BUILD_JOBS="$BUILD_JOBS" \
  bash -s <<'DEBIAN'
set -euo pipefail

SDRPP_REF="${SDRPP_REF:-master}"
BUILD_JOBS="${BUILD_JOBS:-4}"
SDRPP_SRC="$HOME/SDRPlusPlus"
SDRPP_BUILD="$SDRPP_SRC/build"
SDRPP_ROOT="$SDRPP_SRC/root_dev"

export DEBIAN_FRONTEND=noninteractive

apt-get update
apt-get install -y \
  build-essential \
  cmake \
  git \
  libfftw3-dev \
  libglfw3-dev \
  libvolk-dev \
  libzstd-dev \
  libusb-1.0-0-dev \
  librtlsdr-dev \
  libsoapysdr-dev \
  librtaudio-dev \
  libhackrf-dev

if [[ ! -d "$SDRPP_SRC/.git" ]]; then
  echo "[*] Cloning SDR++"
  git clone https://github.com/AlexandreRouma/SDRPlusPlus.git "$SDRPP_SRC"
fi

echo "[*] Updating SDR++"
git -C "$SDRPP_SRC" fetch --tags --prune origin
git -C "$SDRPP_SRC" checkout "$SDRPP_REF"

if git -C "$SDRPP_SRC" show-ref --verify --quiet "refs/remotes/origin/$SDRPP_REF"; then
  git -C "$SDRPP_SRC" reset --hard "origin/$SDRPP_REF"
fi

cmake -S "$SDRPP_SRC" -B "$SDRPP_BUILD" \
  -DCMAKE_BUILD_TYPE=Release \
  -DOPT_BUILD_BLADERF_SOURCE=OFF \
  -DOPT_BUILD_PLUTOSDR_SOURCE=OFF \
  -DOPT_BUILD_AIRSPY_SOURCE=OFF \
  -DOPT_BUILD_AIRSPYHF_SOURCE=OFF

cmake --build "$SDRPP_BUILD" --parallel "$BUILD_JOBS"

[[ -x "$SDRPP_BUILD/sdrpp" ]] || {
  echo "SDR++ build completed but $SDRPP_BUILD/sdrpp was not found." >&2
  exit 1
}

echo "[*] Preparing SDR++ development resources"
cd "$SDRPP_SRC"
./create_root.sh

[[ -d "$SDRPP_ROOT/res" || -d "$SDRPP_ROOT/resources" ]] || {
  echo "SDR++ development root was not created correctly at $SDRPP_ROOT." >&2
  exit 1
}

cat <<EOF

[+] SDR++ build complete
    source:    $SDRPP_SRC
    binary:    $SDRPP_BUILD/sdrpp
    resources: $SDRPP_ROOT

To launch SDR++ in Termux:X11:

    proot-distro login debian --shared-tmp
    export DISPLAY=:1
    cd ~/SDRPlusPlus
    ./build/sdrpp -r root_dev

If your X server uses :1.0 instead, set DISPLAY=:1.0.
EOF
DEBIAN
