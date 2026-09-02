#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

[[ "${PREFIX:-}" == /data/data/com.termux/files/usr* ]] || {
  echo "This run script must be launched from the normal Termux shell." >&2
  exit 2
}

command -v proot-distro >/dev/null 2>&1 || {
  echo "proot-distro is not installed. Run development/termux/setup_sdrpp.sh first." >&2
  exit 1
}

DISPLAY_NUMBER="${DISPLAY_NUMBER:-:1}"
SDRPP_DIR="${SDRPP_DIR:-/root/SDRPlusPlus}"

echo "[*] Starting SDR++ in Debian proot on DISPLAY=$DISPLAY_NUMBER"

exec proot-distro login debian --shared-tmp -- \
  env \
    DISPLAY="$DISPLAY_NUMBER" \
    XDG_RUNTIME_DIR=/tmp/runtime-root \
    XDG_SESSION_TYPE=x11 \
    GDK_BACKEND=x11 \
    LIBGL_ALWAYS_SOFTWARE=1 \
    WAYLAND_DISPLAY= \
  bash -lc '
    set -e
    mkdir -p "$XDG_RUNTIME_DIR"
    chmod 700 "$XDG_RUNTIME_DIR"
    unset WAYLAND_DISPLAY
    cd "'"$SDRPP_DIR"'"
    exec ./build/sdrpp -r root_dev "$@"
  ' bash "$@"
