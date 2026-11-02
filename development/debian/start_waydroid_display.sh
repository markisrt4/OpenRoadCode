#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
set -euo pipefail
if [[ ${1:-} == --help ]]; then
    echo 'Start a dedicated nested Weston kiosk for ORC/Waydroid on an X11 desktop.'
    echo 'Stop the old Waydroid session and Weston first. Leave this terminal running.'
    exit 0
fi
[[ $# == 0 ]] || { echo 'No arguments expected.' >&2; exit 2; }
[[ $EUID -ne 0 ]] || { echo 'Run as your normal desktop user.' >&2; exit 1; }
: "${XDG_RUNTIME_DIR:?Start from your desktop terminal with XDG_RUNTIME_DIR set}"
: "${DISPLAY:?Start from your X11 desktop terminal}"
socket="${ORC_WAYDROID_DISPLAY:-wayland-0}"
[[ $socket != */* ]] || { echo 'Use a socket name, not a path.' >&2; exit 1; }
[[ ! -e "$XDG_RUNTIME_DIR/$socket" ]] || { echo 'The Wayland socket is in use. Stop the previous Weston first.' >&2; exit 1; }
marker="$XDG_RUNTIME_DIR/openroadcode-waydroid-kiosk"
[[ ! -e $marker ]] || { echo 'A kiosk launcher is already recorded. Check its terminal before restarting.' >&2; exit 1; }
weston --backend=x11-backend.so --shell=kiosk-shell.so --socket="$socket" \
    --width=1280 --height=720 --idle-time=0 &
compositor_pid=$!
cleanup() {
    kill "$compositor_pid" 2>/dev/null || true
    wait "$compositor_pid" 2>/dev/null || true
    if [[ -f $marker && $(cat "$marker") == "$compositor_pid" ]]; then rm -f -- "$marker"; fi
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
umask 077
(set -o noclobber; printf '%s\n' "$compositor_pid" > "$marker")
wait "$compositor_pid"
