#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
BUILD_DIR="${OPENROADCODE_RENDERER_BUILD_DIR:-$PROJECT_ROOT/apps/map_renderer/build-termux}"
INSTALL_ROOT="${OPENROADCODE_NAVIGATION_ROOT:-${INSTALL_ROOT:-${PREFIX:-}/opt/openroadcode/navigation}}"
BUILD_JOBS="${BUILD_JOBS:-2}"

[[ "${PREFIX:-}" == /data/data/com.termux/files/usr* ]] || {
  echo "This renderer updater must run inside Termux." >&2
  exit 2
}
[[ -f "$BUILD_DIR/CMakeCache.txt" ]] || {
  echo "Renderer build is not configured: $BUILD_DIR" >&2
  echo "Run ./development/termux/build_navigation_stack.sh first." >&2
  exit 2
}

echo "[*] Installing renderer build dependencies"
pkg install -y clang cmake ninja pkg-config rapidjson spdlog libzmq glfw libx11 mesa-dev

echo "[*] Rebuilding the ORC renderer (reusing installed MapLibre)"
cmake --build "$BUILD_DIR" --parallel "$BUILD_JOBS"
install -Dm755 "$BUILD_DIR/openroadcode-map-renderer" "$INSTALL_ROOT/bin/openroadcode-map-renderer"
echo "[*] Renderer updated. Restart ORC to use the new executable."
