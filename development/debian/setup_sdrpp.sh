#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

SDRPP_REF="${SDRPP_REF:-master}"
BUILD_JOBS="${BUILD_JOBS:-4}"
SDRPP_SRC="${SDRPP_SRC:-$HOME/SDRPlusPlus}"
SDRPP_BUILD="$SDRPP_SRC/build"
SDRPP_ROOT="$SDRPP_SRC/root_dev"

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  SUDO=sudo
else
  SUDO=
fi

echo "[*] Installing SDR++ build dependencies"
$SUDO apt-get update
$SUDO apt-get install -y \
  build-essential \
  cmake \
  git \
  binutils \
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
  -DOPT_BUILD_RIGCTL_SERVER=ON \
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
mkdir -p "$SDRPP_ROOT"
cp -a "$SDRPP_SRC/root/." "$SDRPP_ROOT/"
mkdir -p "$SDRPP_ROOT/modules"
rm -f "$SDRPP_ROOT/modules/"*.so

module_count=0
while IFS= read -r module; do
  if nm -D "$module" 2>/dev/null | grep -Eq '[[:space:]]_INFO_$'; then
    cp -f "$module" "$SDRPP_ROOT/modules/$(basename "$module")"
    module_count=$((module_count + 1))
  fi
done < <(find "$SDRPP_BUILD" -type f -name '*.so' -print)

echo "[*] Installed $module_count SDR++ runtime modules"
[[ -f "$SDRPP_ROOT/modules/rigctl_server.so" ]] || {
  echo "SDR++ Rigctl Server was enabled but rigctl_server.so was not installed." >&2
  exit 1
}

cat > "$SDRPP_ROOT/rigctl_server_config.json" <<'JSON'
{
  "Rigctl Server": {
    "host": "127.0.0.1",
    "port": 4532,
    "tuning": true,
    "recording": false,
    "autoStart": true,
    "vfo": "Radio",
    "recorder": ""
  }
}
JSON

cat <<EOF

[+] SDR++ build complete
    source:    $SDRPP_SRC
    binary:    $SDRPP_BUILD/sdrpp
    resources: $SDRPP_ROOT
    modules:   $module_count
    rigctl:    127.0.0.1:4532 (autostart)

Launch with:

    cd "$SDRPP_SRC"
    ./build/sdrpp -r root_dev
EOF
