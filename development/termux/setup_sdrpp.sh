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
TELEMETRY_SRC="$ORC_ROOT/development/sdrpp/telemetry"

for module_dir in "$REMOTE_CONTROL_SRC" "$TELEMETRY_SRC"; do
  [[ -f "$module_dir/CMakeLists.txt" && -f "$module_dir/src/main.cpp" ]] || {
    echo "OpenRoadCode SDR++ module was not found at $module_dir" >&2
    exit 1
  }
done

SDRPP_REF="${SDRPP_REF:-master}"
BUILD_JOBS="${BUILD_JOBS:-4}"

command -v pkg >/dev/null 2>&1 || {
  echo "Termux pkg command was not found." >&2
  exit 1
}

TERMUX_PACKAGES=(proot-distro git)
missing_termux_packages=()
for package in "${TERMUX_PACKAGES[@]}"; do
  dpkg-query -W -f='${Status}' "$package" 2>/dev/null | grep -q '^install ok installed$' || missing_termux_packages+=("$package")
done
if ((${#missing_termux_packages[@]})); then
  echo "[*] Installing missing Termux packages: ${missing_termux_packages[*]}"
  pkg install -y "${missing_termux_packages[@]}"
else
  echo "[*] Required Termux packages are already installed"
fi

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
  TELEMETRY_SRC="$TELEMETRY_SRC" \
  bash -s <<'DEBIAN'
set -euo pipefail

SDRPP_REF="${SDRPP_REF:-master}"
BUILD_JOBS="${BUILD_JOBS:-4}"
REMOTE_CONTROL_SRC="${REMOTE_CONTROL_SRC:?REMOTE_CONTROL_SRC is required}"
TELEMETRY_SRC="${TELEMETRY_SRC:?TELEMETRY_SRC is required}"
SDRPP_SRC="$HOME/SDRPlusPlus"
SDRPP_BUILD="$SDRPP_SRC/build"
SDRPP_ROOT="$SDRPP_SRC/root_dev"
REMOTE_CONTROL_DST="$SDRPP_SRC/misc_modules/remote_control"
TELEMETRY_DST="$SDRPP_SRC/misc_modules/telemetry"

export DEBIAN_FRONTEND=noninteractive

DEBIAN_PACKAGES=(
  build-essential cmake git binutils python3 libfftw3-dev libglfw3-dev libvolk-dev
  libzstd-dev libusb-1.0-0-dev librtlsdr-dev libsoapysdr-dev librtaudio-dev libhackrf-dev
)
missing_debian_packages=()
for package in "${DEBIAN_PACKAGES[@]}"; do
  dpkg-query -W -f='${Status}' "$package" 2>/dev/null | grep -q '^install ok installed$' || missing_debian_packages+=("$package")
done
if ((${#missing_debian_packages[@]})); then
  echo "[*] Installing missing Debian packages: ${missing_debian_packages[*]}"
  apt-get update
  apt-get install -y "${missing_debian_packages[@]}"
else
  echo "[*] Required Debian packages are already installed"
fi

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

echo "[*] Staging OpenRoadCode SDR++ modules"
rm -rf "$REMOTE_CONTROL_DST" "$TELEMETRY_DST"
cp -a "$REMOTE_CONTROL_SRC" "$REMOTE_CONTROL_DST"
cp -a "$TELEMETRY_SRC" "$TELEMETRY_DST"

python3 - "$SDRPP_SRC/CMakeLists.txt" "$SDRPP_SRC/core/src/core.cpp" "$SDRPP_SRC/core/backends/glfw/backend.cpp" <<'PY'
from pathlib import Path
import sys
cmake_path = Path(sys.argv[1]); core_path = Path(sys.argv[2]); backend_path = Path(sys.argv[3])
cmake = cmake_path.read_text()
for comment, line in (("OpenRoadCode application remote control module", 'add_subdirectory("misc_modules/remote_control")'), ("OpenRoadCode telemetry module", 'add_subdirectory("misc_modules/telemetry")')):
    if line not in cmake: cmake = cmake.rstrip() + f"\n\n# {comment}\n{line}\n"
cmake_path.write_text(cmake)
core = core_path.read_text()
marker = '    defConfig["moduleInstances"]["Rigctl Server"] = "rigctl_server";\n'
if marker not in core: raise SystemExit("Could not locate Rigctl Server default module instance in SDR++ core.cpp")
for instance, module in (("Remote Control", "remote_control"), ("Telemetry", "telemetry")):
    if f'moduleInstances"]["{instance}"]' not in core:
        lines = f'    defConfig["moduleInstances"]["{instance}"]["module"] = "{module}";\n    defConfig["moduleInstances"]["{instance}"]["enabled"] = true;\n'
        core = core.replace(marker, marker + lines, 1)
core_path.write_text(core)

# Embedded ORC launches ask GLFW to create the client hidden. X11 can then
# reparent and map it inside the Tk host without a one-frame desktop flash.
backend = backend_path.read_text()
hidden_marker = '        if (!glfwInit()) {\n            return 1;\n        }\n'
hidden_code = hidden_marker + '\n        if (std::getenv("ORC_SDRPP_START_HIDDEN") != nullptr) {\n            glfwWindowHint(GLFW_VISIBLE, GLFW_FALSE);\n        }\n'
if 'ORC_SDRPP_START_HIDDEN' not in backend:
    if hidden_marker not in backend:
        raise SystemExit("Could not locate GLFW initialization in SDR++ backend.cpp")
    if '#include <cstdlib>\n' not in backend:
        backend = backend.replace('#include <filesystem>\n', '#include <filesystem>\n#include <cstdlib>\n', 1)
    backend = backend.replace(hidden_marker, hidden_code, 1)
backend_path.write_text(backend)
PY

cmake -S "$SDRPP_SRC" -B "$SDRPP_BUILD" -DCMAKE_BUILD_TYPE=Release -DOPT_BUILD_RIGCTL_SERVER=ON -DOPT_BUILD_BLADERF_SOURCE=OFF -DOPT_BUILD_PLUTOSDR_SOURCE=OFF -DOPT_BUILD_AIRSPY_SOURCE=OFF -DOPT_BUILD_AIRSPYHF_SOURCE=OFF
cmake --build "$SDRPP_BUILD" --parallel "$BUILD_JOBS"
[[ -x "$SDRPP_BUILD/sdrpp" ]] || { echo "SDR++ build completed but $SDRPP_BUILD/sdrpp was not found." >&2; exit 1; }

echo "[*] Preparing SDR++ development resources"
mkdir -p "$SDRPP_ROOT"; cp -a "$SDRPP_SRC/root/." "$SDRPP_ROOT/"
RIGCTL_MODULE="$(find "$SDRPP_BUILD" -type f -name 'rigctl_server.so' -print -quit)"
REMOTE_CONTROL_MODULE="$(find "$SDRPP_BUILD" -type f -name 'remote_control.so' -print -quit)"
TELEMETRY_MODULE="$(find "$SDRPP_BUILD" -type f -name 'telemetry.so' -print -quit)"
for pair in "Rigctl Server:$RIGCTL_MODULE" "OpenRoadCode remote control:$REMOTE_CONTROL_MODULE" "OpenRoadCode telemetry:$TELEMETRY_MODULE"; do name="${pair%%:*}"; file="${pair#*:}"; [[ -n "$file" ]] || { echo "$name module was not produced." >&2; exit 1; }; done
for module in "$REMOTE_CONTROL_MODULE" "$TELEMETRY_MODULE"; do
  echo "[*] Verifying $(basename "$module") SDR++ ABI exports"
  for symbol in _INFO_ _INIT_ _CREATE_INSTANCE_ _DELETE_INSTANCE_ _END_; do nm -D "$module" 2>/dev/null | grep -Eq "[[:space:]]${symbol}$" || { echo "$(basename "$module") is missing required SDR++ symbol: $symbol" >&2; exit 1; }; done
done
mkdir -p "$SDRPP_ROOT/modules"; rm -f "$SDRPP_ROOT/modules/"*.so
cp -f "$RIGCTL_MODULE" "$SDRPP_ROOT/modules/rigctl_server.so"
cp -f "$REMOTE_CONTROL_MODULE" "$SDRPP_ROOT/modules/remote_control.so"
cp -f "$TELEMETRY_MODULE" "$SDRPP_ROOT/modules/telemetry.so"

if [[ -f "$SDRPP_ROOT/config.json" ]]; then
  echo "[*] Enabling SDR++ integration module instances"
  python3 - "$SDRPP_ROOT/config.json" <<'PY'
import json, sys
from pathlib import Path
path=Path(sys.argv[1]); data=json.loads(path.read_text()); instances=data.setdefault("moduleInstances", {})
instances.pop("ORC Telemetry", None)
instances["Remote Control"]={"module":"remote_control","enabled":True}
instances["Telemetry"]={"module":"telemetry","enabled":True}
path.write_text(json.dumps(data, indent=4)+"\n")
PY
fi

cat > "$SDRPP_ROOT/rigctl_server_config.json" <<'EOF'
{"Rigctl Server":{"host":"127.0.0.1","port":4532,"tuning":true,"recording":false,"autoStart":true,"vfo":"Radio","recorder":""}}
EOF

cat <<EOF
[+] SDR++ build complete
    source:         $SDRPP_SRC
    binary:         $SDRPP_BUILD/sdrpp
    resources:      $SDRPP_ROOT
    modules:        rigctl_server.so, remote_control.so, telemetry.so
    rigctl:         127.0.0.1:4532
    remote control: 127.0.0.1:4533
    telemetry:      127.0.0.1:4534
EOF
DEBIAN
