#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
set -euo pipefail
umask 077
usage() {
    echo "Usage: bash development/debian/waydroid_system_bars.sh hide PACKAGE | restore"
    echo "Hide Android status/navigation bars for one app, or restore the previous policy."
    echo "Requires a running Waydroid and sudo; does not hide ORC's Back control."
}
fail() { echo "Error: $*" >&2; exit 1; }
case "${1:-}" in
    --help|-h) usage; exit 0 ;;
    hide) [[ $# == 2 && $2 =~ ^[A-Za-z][A-Za-z0-9_]*(\.[A-Za-z0-9_]+)+$ ]] || { usage >&2; exit 2; } ;;
    restore) [[ $# == 1 ]] || { usage >&2; exit 2; } ;;
    *) usage >&2; exit 2 ;;
esac
[[ $EUID -ne 0 ]] || fail 'Run as your desktop user, not as root.'
state_dir="${XDG_STATE_HOME:-$HOME/.local/state}/openroadcode"
backup="$state_dir/waydroid-system-bars"
if [[ $1 == hide ]]; then
    [[ ! -e $backup ]] || fail 'An override is already recorded. Run restore first.'
    previous=$(sudo waydroid shell -- settings get global policy_control)
    previous=${previous//$'\r'/}
    # Avoid replacing unrelated apps' immersive policies.
    # Some experimental images/setups contain the literal malformed value
    # "null*". It is not an immersive rule; preserve it for exact restoration.
    [[ -z $previous || $previous == null || $previous == 'null*' ]] || fail 'An existing Android immersive policy is configured; it was left unchanged.'
    policy="immersive.full=$2"
    mkdir -p "$state_dir"
    printf '%s\n%s\n' "$policy" "$previous" > "$backup"
    sudo waydroid shell -- settings put global policy_control "$policy"
    echo "Android bars hidden for $2. Swipe from an edge to reveal them temporarily."
    echo "Use restore to remove this experiment. ORC's Back control remains available."
else
    [[ -f $backup ]] || fail 'No saved override exists for this user.'
    { IFS= read -r policy; IFS= read -r previous || true; } < "$backup"
    current=$(sudo waydroid shell -- settings get global policy_control)
    current=${current//$'\r'/}
    [[ $current == "$policy" || $current == "$previous" ]] || fail 'Android policy changed elsewhere; refusing to overwrite it.'
    if [[ -z $previous || $previous == null ]]; then
        sudo waydroid shell -- settings delete global policy_control
    else
        sudo waydroid shell -- settings put global policy_control "$previous"
    fi
    rm -f -- "$backup"
    echo 'Previous Android system-bar policy restored.'
fi
