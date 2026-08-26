#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
set -euo pipefail

REMOTE="${NAV_DATA_REMOTE:-${1:-}}"
REMOTE_ROOT="${NAV_DATA_REMOTE_ROOT:-/srv/openroadcode}"
DATA_ROOT="${NAV_DATA_ROOT:-$HOME/.local/share/openroadcode}"
STAGING="${DATA_ROOT}.staging"
BACKUP="${DATA_ROOT}.previous"

[[ -n "$REMOTE" ]] || {
  echo "Usage: NAV_DATA_REMOTE=user@map-host $0" >&2
  echo "   or: $0 user@map-host" >&2
  exit 2
}
command -v rsync >/dev/null || { echo "rsync is required (pkg install rsync)" >&2; exit 2; }
command -v ssh >/dev/null || { echo "ssh is required (pkg install openssh)" >&2; exit 2; }

mkdir -p "$STAGING"
echo "[*] Pulling navigation data from $REMOTE:$REMOTE_ROOT/"
rsync --archive --delete-delay --partial --human-readable --info=progress2 \
  --exclude=maps/routes/ \
  "$REMOTE:$REMOTE_ROOT/" "$STAGING/"

[[ -f "$STAGING/build-manifest.json" ]] || {
  echo "Pulled data is missing build-manifest.json; refusing to activate it." >&2
  exit 1
}

mkdir -p "$DATA_ROOT/maps/routes"
if [[ -d "$DATA_ROOT/maps/routes" ]]; then
  mkdir -p "$STAGING/maps/routes"
  rsync --archive "$DATA_ROOT/maps/routes/" "$STAGING/maps/routes/"
fi

rm -rf "$BACKUP"
if [[ -d "$DATA_ROOT" ]]; then mv "$DATA_ROOT" "$BACKUP"; fi
mv "$STAGING" "$DATA_ROOT"
echo "[+] Navigation data activated at $DATA_ROOT"
echo "    Previous dataset: $BACKUP"
