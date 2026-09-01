#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ORC_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
REMOTE_CONTROL_SRC="$ORC_ROOT/development/sdrpp/remote_control"

[[ -f "$REMOTE_CONTROL_SRC/CMakeLists.txt" && -f "$REMOTE_CONTROL_SRC/src/main.cpp" ]] || {
  echo "OpenRoadCode SDR++ remote_control module was not found at $REMOTE_CONTROL_SRC" >&2
  exit 1
}

SDRPP_REF="${SDRPP_REF:-master}"
BUILD_JOBS="${BUILD_JOBS:-4}"
SDRPP_SRC="${SDRPP_SRC:-$HOME/SDRPlusPlus}"
SDRPP_BUILD="$SDRPP_SRC/build"
SDRPP_ROOT="$SDRPP_SRC/root_dev"
REMOTE_CONTROL_DST="$SDRPP_SRC/misc_modules/remote_control"

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

echo "[*] Staging OpenRoadCode remote_control SDR++ module"
rm -rf "$REMOTE_CONTROL_DST"
cp -a "$REMOTE_CONTROL_SRC" "$REMOTE_CONTROL_DST"

python3 - "$SDRPP_SRC/CMakeLists.txt" "$SDRPP_SRC/core/src/core.cpp" <<'PY'
from pathlib import Path
import sys

cmake_path = Path(sys.argv[1])
core_path = Path(sys.argv[2])

cmake = cmake_path.read_text()
cmake_line = 'add_subdirectory("misc_modules/remote_control")'
if cmake_line not in cmake:
    cmake = cmake.rstrip() + f"\n\n# OpenRoadCode application remote control module\n{cmake_line}\n"
    cmake_path.write_text(cmake)

core = core_path.read_text()
instance_lines = (
    '    defConfig["moduleInstances"]["Remote Control"]["module"] = "remote_control";\n'
    '    defConfig["moduleInstances"]["Remote Control"]["enabled"] = true;\n'
)
if 'moduleInstances"]["Remote Control"]' not in core:
    marker = '    defConfig["moduleInstances"]["Rigctl Server"] = "rigctl_server";\n'
    if marker not in core:
        raise SystemExit("Could not locate Rigctl Server default module instance in SDR++ core.cpp")
    core = core.replace(marker, marker + instance_lines, 1)
    core_path.write_text(core)
PY

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
[[ -f "$SDRPP_ROOT/modules/remote_control.so" ]] || {
  echo "OpenRoadCode remote_control.so was not installed." >&2
  exit 1
}

echo "[*] Verifying remote_control SDR++ ABI exports"
for symbol in _INFO_ _INIT_ _CREATE_INSTANCE_ _DELETE_INSTANCE_ _END_; do
  if ! nm -D "$SDRPP_ROOT/modules/remote_control.so" 2>/dev/null | grep -Eq "[[:space:]]${symbol}$"; then
    echo "remote_control.so is missing required SDR++ symbol: $symbol" >&2
    exit 1
  fi
done

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
    source:         $SDRPP_SRC
    binary:         $SDRPP_BUILD/sdrpp
    resources:      $SDRPP_ROOT
    modules:        $module_count (includes remote_control.so)
    rigctl:         127.0.0.1:4532 (autostart)
    remote control: 127.0.0.1:4533
    ABI check:      _INFO_ _INIT_ _CREATE_INSTANCE_ _DELETE_INSTANCE_ _END_ OK

Launch with:

    cd "$SDRPP_SRC"
    ./build/sdrpp -r root_dev
EOF
