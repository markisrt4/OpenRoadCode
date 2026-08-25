#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
TOOLCHAIN_LOCK="$PROJECT_ROOT/tools/map_builder/toolchain.lock"

[[ "${PREFIX:-}" == /data/data/com.termux/files/usr* ]] || {
  echo "This experimental builder must run inside Termux." >&2
  exit 2
}

# shellcheck disable=SC1090
source "$TOOLCHAIN_LOCK"

HOST_SRC="${HOST_SRC:-$HOME/src}"
MAPLIBRE_SRC="${MAPLIBRE_SRC:-$HOST_SRC/maplibre-native}"
VALHALLA_SRC="${VALHALLA_SRC:-$HOST_SRC/valhalla}"
PRIME_SERVER_SRC="${PRIME_SERVER_SRC:-$HOST_SRC/prime_server}"
MAPLIBRE_REF="${MAPLIBRE_REF:-b0388d186d582a8535aa3c03e3cc2ef98cb70dc0}"
VALHALLA_REF="${VALHALLA_REF:-$VALHALLA_COMMIT}"
BUILD_JOBS="${BUILD_JOBS:-$(nproc)}"
INSTALL_ROOT="${INSTALL_ROOT:-$PREFIX/opt/openroadcode/navigation}"
CONFIG_ROOT="${CONFIG_ROOT:-$PREFIX/etc/openroadcode}"
DATA_ROOT="${DATA_ROOT:-$HOME/.local/share/openroadcode}"

checkout_repo() {
  local url="$1" dir="$2" ref="$3"
  if [[ ! -d "$dir/.git" ]]; then git clone "$url" "$dir"; fi
  git -C "$dir" fetch --tags --prune origin
  git -C "$dir" checkout --detach "$ref"
  git -C "$dir" submodule sync --recursive
  git -C "$dir" submodule update --init --recursive
}

apply_patch_once() {
  local dir="$1" patch_file="$2"
  if git -C "$dir" apply --reverse --check "$patch_file" >/dev/null 2>&1; then
    echo "[*] Patch already applied: $(basename "$patch_file")"
  else
    git -C "$dir" apply --check "$patch_file"
    git -C "$dir" apply "$patch_file"
  fi
}

echo "[*] Installing Termux build dependencies"
pkg install -y x11-repo
pkg install -y \
  git clang cmake ninja pkg-config patch \
  boost protobuf libsqlite libspatialite libcurl liblz4 zeromq czmq \
  luajit geos libpng libjpeg-turbo libwebp libicu rapidjson \
  mesa mesa-dev glfw libx11 libx11-dev xorgproto

mkdir -p "$HOST_SRC" "$INSTALL_ROOT" "$CONFIG_ROOT" "$DATA_ROOT"

# prime_server is intentionally built first and installed into PREFIX so
# Valhalla's native Termux build can discover it normally.
if [[ ! -d "$PRIME_SERVER_SRC/.git" ]]; then
  git clone https://github.com/kevinkreiser/prime_server.git "$PRIME_SERVER_SRC"
fi
cmake -S "$PRIME_SERVER_SRC" -B "$PRIME_SERVER_SRC/build-termux" -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX="$PREFIX"
cmake --build "$PRIME_SERVER_SRC/build-termux" -j"$BUILD_JOBS"
cmake --install "$PRIME_SERVER_SRC/build-termux"

checkout_repo https://github.com/valhalla/valhalla.git "$VALHALLA_SRC" "$VALHALLA_REF"
apply_patch_once "$VALHALLA_SRC" "$SCRIPT_DIR/patches/valhalla-streampos.patch"
rm -rf "$VALHALLA_SRC/build-termux"
cmake -S "$VALHALLA_SRC" -B "$VALHALLA_SRC/build-termux" -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX="$INSTALL_ROOT/valhalla" \
  -DCMAKE_EXE_LINKER_FLAGS=-llog \
  -DCMAKE_SHARED_LINKER_FLAGS=-llog \
  -DENABLE_TESTS=OFF \
  -DENABLE_BENCHMARKS=OFF \
  -DENABLE_PYTHON_BINDINGS=OFF \
  -DENABLE_TOOLS=ON \
  -DENABLE_DATA_TOOLS=ON \
  -DENABLE_HTTP=ON \
  -DENABLE_SERVICES=ON \
  -DENABLE_SINGLE_FILES_WERROR=OFF
cmake --build "$VALHALLA_SRC/build-termux" -j"$BUILD_JOBS"
cmake --install "$VALHALLA_SRC/build-termux"

checkout_repo https://github.com/maplibre/maplibre-native.git "$MAPLIBRE_SRC" "$MAPLIBRE_REF"
rm -rf "$MAPLIBRE_SRC/build-termux-glfw"
cmake -S "$MAPLIBRE_SRC" -B "$MAPLIBRE_SRC/build-termux-glfw" -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_SYSTEM_NAME=Linux \
  -DMLN_WITH_CORE_ONLY=OFF \
  -DMLN_WITH_GLFW=ON \
  -DMLN_WITH_OPENGL=ON \
  -DMLN_WITH_EGL=OFF \
  -DMLN_WITH_VULKAN=OFF \
  -DMLN_WITH_WERROR=OFF \
  -DX11_X11_INCLUDE_PATH="$PREFIX/include" \
  -DX11_X11_LIB="$PREFIX/lib/libX11.so"
cmake --build "$MAPLIBRE_SRC/build-termux-glfw" -j"$BUILD_JOBS"

MBGL_GLFW="$MAPLIBRE_SRC/build-termux-glfw/platform/glfw/mbgl-glfw"
[[ -x "$MBGL_GLFW" ]] || { echo "MapLibre GLFW executable was not produced." >&2; exit 1; }
install -Dm755 "$MBGL_GLFW" "$INSTALL_ROOT/bin/mbgl-glfw"

if [[ ! -f "$CONFIG_ROOT/navigation.toml" ]]; then
  install -m 0644 "$PROJECT_ROOT/config/navigation.toml" "$CONFIG_ROOT/navigation.toml"
fi

cat <<EOF

[+] Experimental Termux navigation build complete
    Valhalla: $INSTALL_ROOT/valhalla/bin/valhalla_service
    MapLibre: $INSTALL_ROOT/bin/mbgl-glfw
    config:   $CONFIG_ROOT/navigation.toml
    data:     $DATA_ROOT

Termux:X11 Android APK is required for graphical execution.
Start it with:
    termux-x11 :0 &
    export DISPLAY=:0
    $INSTALL_ROOT/bin/mbgl-glfw
EOF
