#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE="$ROOT/build-output/"
DEST="/srv/openroadcode/"
REMOTE=""
TERMUX_REMOTE=""
TERMUX_DEST=".local/share/openroadcode/"

usage() {
  cat <<'EOF'
Usage: deploy-to-srv.sh [--remote USER@HOST | --termux USER@HOST]

Deploy validated build-output to a local/remote Linux target or directly to
an OpenRoadCode Termux runtime.

Modes:
  no option            install locally at /srv/openroadcode (sudo)
  --remote USER@HOST   install remotely at /srv/openroadcode (sudo)
  --termux USER@HOST   install in ~/.local/share/openroadcode (no sudo)

Examples:
  ./scripts/deploy-to-srv.sh
  ./scripts/deploy-to-srv.sh --remote openroad@192.168.1.50
  ./scripts/deploy-to-srv.sh --termux u0_a123@192.168.1.75
EOF
}

case "${1:-}" in
  "") ;;
  --remote)
    [[ $# -eq 2 ]] || { usage >&2; exit 2; }
    REMOTE="$2"
    ;;
  --termux)
    [[ $# -eq 2 ]] || { usage >&2; exit 2; }
    TERMUX_REMOTE="$2"
    ;;
  -h|--help)
    usage
    exit 0
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac

[[ -f "$SOURCE/build-manifest.json" ]] || {
  echo "No validated build-output/build-manifest.json found. Build first." >&2
  exit 2
}

RSYNC_OPTIONS=(
  --archive
  --delete-delay
  --partial
  --human-readable
  --info=progress2
  --exclude=maps/routes/
)

if [[ -n "$TERMUX_REMOTE" ]]; then
  echo "Checking Termux deployment prerequisites on $TERMUX_REMOTE"
  if ! ssh "$TERMUX_REMOTE" "command -v rsync >/dev/null && mkdir -p '$TERMUX_DEST/maps/routes'"; then
    echo "Termux deployment requires SSH access and rsync on $TERMUX_REMOTE." >&2
    exit 2
  fi
  echo "Deploying validated OpenRoadCode map data to $TERMUX_REMOTE:~/$TERMUX_DEST"
  rsync "${RSYNC_OPTIONS[@]}" "$SOURCE" "$TERMUX_REMOTE:$TERMUX_DEST"
  echo "Deployment complete. Termux data root: ~/$TERMUX_DEST"
elif [[ -z "$REMOTE" ]]; then
  sudo mkdir -p "$DEST/maps/routes"
  echo "Deploying validated OpenRoadCode map data to $DEST"
  sudo rsync "${RSYNC_OPTIONS[@]}" "$SOURCE" "$DEST"
  echo "Deployment complete. Runtime routes in ${DEST}maps/routes/ were preserved."
else
  echo "Checking remote deployment prerequisites on $REMOTE"
  if ! ssh "$REMOTE" "command -v rsync >/dev/null && sudo -n mkdir -p '$DEST/maps/routes'"; then
    echo "Remote deployment requires rsync and passwordless sudo for $REMOTE." >&2
    exit 2
  fi
  echo "Deploying validated OpenRoadCode map data to $REMOTE:$DEST"
  rsync "${RSYNC_OPTIONS[@]}" \
    --rsync-path="sudo -n rsync" \
    "$SOURCE" \
    "$REMOTE:$DEST"
  echo "Deployment complete. Runtime routes in ${DEST}maps/routes/ were preserved."
fi
