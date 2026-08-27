#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"

[[ "${PREFIX:-}" == /data/data/com.termux/files/usr* ]] || {
  echo "This experimental builder must run inside Termux." >&2
  exit 2
}

HOST_SRC="${HOST_SRC:-$HOME/src}"
MAPLIBRE_SRC="${MAPLIBRE_SRC:-$HOST_SRC/maplibre-native}"
VALHALLA_SRC="${VALHALLA_SRC:-$HOST_SRC/valhalla}"
PRIME_SERVER_SRC="${PRIME_SERVER_SRC:-$HOST_SRC/prime_server}"
CPPZMQ_SRC="${CPPZMQ_SRC:-$HOST_SRC/cppzmq}"
MAPLIBRE_REF="${MAPLIBRE_REF:-b0388d186d582a8535aa3c03e3cc2ef98cb70dc0}"
VALHALLA_REF="${VALHALLA_REF:-a60c7cbfc83e073f50887cd27e0109d02e6b64e5}"
CPPZMQ_REF="${CPPZMQ_REF:-v4.11.0}"
BUILD_JOBS="${BUILD_JOBS:-$(nproc)}"
INSTALL_ROOT="${INSTALL_ROOT:-$PREFIX/opt/openroadcode/navigation}"
CONFIG_ROOT="${CONFIG_ROOT:-$PREFIX/etc/openroadcode}"
DATA_ROOT="${DATA_ROOT:-$HOME/.local/share/openroadcode}"
FORCE_REBUILD="${FORCE_REBUILD:-0}"
X11_DISPLAY="${X11_DISPLAY:-:1}"

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

should_build() {
  local artifact="$1"
  [[ "$FORCE_REBUILD" == "1" || ! -e "$artifact" ]]
}

prime_server_installed() {
  compgen -G "$PREFIX/lib/libprime_server.so*" >/dev/null
}

echo "[*] Installing Termux build dependencies"
pkg install -y x11-repo
pkg update
pkg install -y \
  git clang cmake ninja pkg-config patch \
  boost boost-headers protobuf libsqlite libspatialite spatialite-tools libcurl liblz4 libzmq libczmq \
  luajit libgeos libpng libjpeg-turbo libwebp libicu rapidjson \
  mesa mesa-dev glfw libx11 xorgproto

for command in git clang cmake ninja pkg-config spatialite spatialite_tool; do
  command -v "$command" >/dev/null || {
    echo "Missing required build command after package installation: $command" >&2
    exit 1
  }
done

mkdir -p "$HOST_SRC" "$INSTALL_ROOT" "$CONFIG_ROOT" "$DATA_ROOT"

if [[ "$FORCE_REBUILD" == "1" ]] || ! prime_server_installed; then
  echo "[*] Building prime_server"
  if [[ ! -d "$PRIME_SERVER_SRC/.git" ]]; then
    git clone https://github.com/kevinkreiser/prime_server.git "$PRIME_SERVER_SRC"
  fi
  git -C "$PRIME_SERVER_SRC" submodule sync --recursive
  git -C "$PRIME_SERVER_SRC" submodule update --init --recursive
  cmake -S "$PRIME_SERVER_SRC" -B "$PRIME_SERVER_SRC/build-termux" -G Ninja \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_INSTALL_PREFIX="$PREFIX"
  cmake --build "$PRIME_SERVER_SRC/build-termux" -j"$BUILD_JOBS"
  cmake --install "$PRIME_SERVER_SRC/build-termux"
else
  echo "[*] prime_server already installed; skipping build"
fi

if [[ "$FORCE_REBUILD" == "1" || ! -f "$PREFIX/include/zmq.hpp" ]]; then
  echo "[*] Installing cppzmq headers"
  checkout_repo https://github.com/zeromq/cppzmq.git "$CPPZMQ_SRC" "$CPPZMQ_REF"
  install -Dm644 "$CPPZMQ_SRC/zmq.hpp" "$PREFIX/include/zmq.hpp"
  install -Dm644 "$CPPZMQ_SRC/zmq_addon.hpp" "$PREFIX/include/zmq_addon.hpp"
else
  echo "[*] cppzmq headers already installed; skipping install"
fi

VALHALLA_SERVICE="$INSTALL_ROOT/valhalla/bin/valhalla_service"
if should_build "$VALHALLA_SERVICE"; then
  echo "[*] Building Valhalla"
  checkout_repo https://github.com/valhalla/valhalla.git "$VALHALLA_SRC" "$VALHALLA_REF"
  apply_patch_once "$VALHALLA_SRC" "$SCRIPT_DIR/patches/valhalla-streampos.patch"
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
else
  echo "[*] Valhalla already installed at $VALHALLA_SERVICE; skipping build"
fi

MBGL_INSTALLED="$INSTALL_ROOT/bin/mbgl-glfw"
if should_build "$MBGL_INSTALLED"; then
  echo "[*] Building MapLibre"
  checkout_repo https://github.com/maplibre/maplibre-native.git "$MAPLIBRE_SRC" "$MAPLIBRE_REF"
  apply_patch_once "$MAPLIBRE_SRC" "$SCRIPT_DIR/patches/maplibre-android-thread-name.patch"
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
  install -Dm755 "$MBGL_GLFW" "$MBGL_INSTALLED"
else
  echo "[*] MapLibre already installed at $MBGL_INSTALLED; skipping build"
fi

MAP_RENDERER_INSTALLED="$INSTALL_ROOT/bin/openroadcode-map-renderer"
if should_build "$MAP_RENDERER_INSTALLED"; then
  echo "[*] Building OpenRoadCode map renderer"
  cmake -S "$PROJECT_ROOT/apps/map_renderer" \
    -B "$PROJECT_ROOT/apps/map_renderer/build-termux" -G Ninja \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_SYSTEM_NAME=Linux \
    -DMAPLIBRE_ROOT="$MAPLIBRE_SRC" \
    -DMAPLIBRE_BUILD="$MAPLIBRE_SRC/build-termux-glfw"
  cmake --build "$PROJECT_ROOT/apps/map_renderer/build-termux" -j"$BUILD_JOBS"
  install -Dm755 \
    "$PROJECT_ROOT/apps/map_renderer/build-termux/openroadcode-map-renderer" \
    "$MAP_RENDERER_INSTALLED"
else
  echo "[*] OpenRoadCode map renderer already installed at $MAP_RENDERER_INSTALLED; skipping build"
fi

NAVIGATION_CONFIG_SOURCE="$PROJECT_ROOT/config/navigation.toml"
if [[ -f "$NAVIGATION_CONFIG_SOURCE" && ! -f "$CONFIG_ROOT/navigation.toml" ]]; then
  install -m 0644 "$NAVIGATION_CONFIG_SOURCE" "$CONFIG_ROOT/navigation.toml"
elif [[ ! -f "$NAVIGATION_CONFIG_SOURCE" ]]; then
  echo "[*] No config/navigation.toml in this checkout; skipping optional config install"
fi

cat <<EOF

[+] Experimental Termux navigation build complete
    Valhalla:     $VALHALLA_SERVICE
    MapLibre:     $MBGL_INSTALLED
    ORC renderer: $MAP_RENDERER_INSTALLED
    config:       $CONFIG_ROOT/navigation.toml (optional)
    data:         $DATA_ROOT

Set FORCE_REBUILD=1 to rebuild all native components.
Set X11_DISPLAY to override the Termux:X11 display (default: :1).

Termux:X11 Android APK is required for graphical execution.
Start the ORC renderer with:
    ./development/termux/start_map_renderer.sh
EOF
