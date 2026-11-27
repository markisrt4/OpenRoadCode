#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Root-owned, fixed-purpose bridge to the SDRForge user's systemd manager.
set -euo pipefail
[[ $# -eq 1 ]] || exit 2
case "$1" in start|stop|restart|is-active|show) ;; *) exit 2 ;; esac
CONFIG=/etc/openroadcode/sdrforge-user
[[ -f "$CONFIG" ]] || { echo "SDRForge user not configured" >&2; exit 1; }
IFS= read -r account < "$CONFIG"
[[ "$account" =~ ^[a-z_][a-z0-9_-]*$ ]] || exit 1
uid="$(id -u "$account")"
[[ "$uid" -ge 1000 ]] || { echo "Refusing system account" >&2; exit 1; }
[[ -S "/run/user/$uid/bus" ]] || { echo "SDRForge user bus unavailable" >&2; exit 1; }
args=("$1" libsdrforge.service)
if [[ "$1" == show ]]; then args+=(--property=ActiveState,SubState,UnitFileState --value); fi
exec /usr/sbin/runuser -u "$account" -- /usr/bin/env \
  "XDG_RUNTIME_DIR=/run/user/$uid" \
  "DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$uid/bus" \
  /usr/bin/systemctl --user "${args[@]}"
