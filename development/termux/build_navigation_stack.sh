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
MAPLIBRE_REF="${MAPLIBRE_REF:-b0388d186d582a8535aa3c03e3cc2ef98cb70dc0}"
VALHALLA_REF="${VALHALLA_REF:-a60c7cbfc83e073f50887cd27e0109d02e6b64e5}"
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
  git clang cmake ninja pkg-config patch python python-pillow \
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

VALHALLA_SERVICE="$INSTALL_ROOT/valhalla/bin/valhalla_service"
