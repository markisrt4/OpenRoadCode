#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

[[ "${PREFIX:-}" == /data/data/com.termux/files/usr* ]] || {
  echo "This setup script must run inside Termux." >&2
  exit 2
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ORC_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
REMOTE_CONTROL_SRC="$ORC_ROOT/development/sdrpp/remote_control"

[[ -f "$REMOTE_CONTROL_SRC/CMakeLists.txt" && -f "$REMOTE_CONTROL_SRC/src/main.cpp" ]] || {
  echo "OpenRoadCode SDR++ remote_control module was not found at $REMOTE_CONTROL_SRC" >&2
  exit 1
}

SDRPP_REF="${SDRPP_REF:-master}"
BUILD_JOBS="${BUILD_JOBS:-4}"

command -v pkg >/dev/null 2>&1 || {
  echo "Termux pkg command was not found." >&2
  exit 1
}

echo "[*] Installing Termux proot support"
pkg install -y proot-distro git

# Probe Debian by actually entering it. This avoids relying on proot-distro's
# human-readable list output or internal installation paths, both of which can
# vary between releases.
if proot-distro login debian -- /bin/true >/dev/null 2>&1; then
  echo "[*] Debian proot is already installed"
else
  echo "[*] Installing Debian proot"
  proot-distro install debian
fi

echo "[*] Installing SDR++ dependencies and building inside Debian"
proot-distro login debian --shared-tmp -- env \
  SDRPP_REF="$SDRPP_REF" \
  BUILD_JOBS="$BUILD_JOBS" \
  REMOTE_CONTROL_SRC="$REMOTE_CONTROL_SRC" \
  bash -s <<'DEBIAN'
set -euo pipefail

SDRPP_REF="${SDRPP_REF:-master}"
BUILD_JOBS="${BUILD_JOBS:-4}"
REMOTE_CONTROL_SRC="${REMOTE_CONTROL_SRC:?REMOTE_CONTROL_SRC is required}"
SDRPP_SRC="$HOME/SDRPlusPlus"
SDRPP_BUILD="$SDRPP_SRC/build"
SDRPP_ROOT="$SDRPP_SRC/root_dev"
REMOTE_CONTROL_DST="$SDRPP_SRC/misc_modules/remote_control"

export DEBIAN_FRONTEND=noninteractive

apt-get update
apt-get install -y \
  build-essential \
  cmake \
  git \
  binutils \
  python3 \
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

RIGCTL_MODULE="$(find "$SDRPP_BUILD" -type f -name 'rigctl_server.so' -print -quit)"
REMOTE_CONTROL_MODULE="$(find "$SDRPP_BUILD" -type f -name 'remote_control.so' -print -quit)"

[[ -n "$RIGCTL_MODULE" ]] || {
  echo "SDR++ Rigctl Server was enabled but rigctl_server.so was not produced." >&2
  exit 1
}
[[ -n "$REMOTE_CONTROL_MODULE" ]] || {
  echo "OpenRoadCode remote_control.so was not produced." >&2
  exit 1
}

echo "[*] Verifying remote_control SDR++ ABI exports"
for symbol in _INFO_ _INIT_ _CREATE_INSTANCE_ _DELETE_INSTANCE_ _END_; do
  if ! nm -D "$REMOTE_CONTROL_MODULE" 2>/dev/null | grep -Eq "[[:space:]]${symbol}$"; then
    echo "remote_control.so is missing required SDR++ symbol: $symbol" >&2
    exit 1
  fi
done

# Termux/proot does not provide a normal desktop audio stack. Loading every
# desktop SDR++ module here can crash during module initialization. Keep the
# embedded ORC runtime deliberately minimal and only install tested modules.
mkdir -p "$SDRPP_ROOT/modules"
rm -f "$SDRPP_ROOT/modules/"*.so
cp -f "$RIGCTL_MODULE" "$SDRPP_ROOT/modules/rigctl_server.so"
cp -f "$REMOTE_CONTROL_MODULE" "$SDRPP_ROOT/modules/remote_control.so"

# Existing root_dev configurations predate the OpenRoadCode remote-control
# module, so patch them too. Patching core.cpp above only affects configs SDR++
# creates from scratch.
if [[ -f "$SDRPP_ROOT/config.json" ]]; then
  echo "[*] Enabling Remote Control instance in existing SDR++ config"
  python3 - "$SDRPP_ROOT/config.json" <<'PY'
import json
from pathlib import Path
import sys

path = Path(sys.argv[1])
data = json.loads(path.read_text())
data.setdefault("moduleInstances", {})["Remote Control"] = {
    "module": "remote_control",
    "enabled": True,
}
path.write_text(json.dumps(data, indent=4) + "\n")
PY
fi

cat > "$SDRPP_ROOT/rigctl_server_config.json" <<'EOF'
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
EOF

cat <<EOF

[+] SDR++ build complete
    source:         $SDRPP_SRC
    binary:         $SDRPP_BUILD/sdrpp
    resources:      $SDRPP_ROOT
    modules:        rigctl_server.so, remote_control.so
    rigctl:         127.0.0.1:4532 (autostart enabled)
    remote control: 127.0.0.1:4533
    ABI check:      _INFO_ _INIT_ _CREATE_INSTANCE_ _DELETE_INSTANCE_ _END_ OK

To launch SDR++ in Termux:X11:

    proot-distro login debian --shared-tmp
    export DISPLAY=:1
    cd ~/SDRPlusPlus
    ./build/sdrpp -r root_dev

If your X server uses :1.0 instead, set DISPLAY=:1.0.
EOF
DEBIAN
