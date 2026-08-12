#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE="$ROOT/build-output/"
DEST="/srv/openroadcode/"
REMOTE=""

usage() {
  cat <<'EOF'
Usage: deploy-to-srv.sh [--remote USER@HOST]

Deploy build-output to /srv/openroadcode on this host or a remote SSH host.
Remote deployment requires rsync and passwordless sudo on the destination.

Examples:
  ./scripts/deploy-to-srv.sh
  ./scripts/deploy-to-srv.sh --remote openroad@192.168.1.50
EOF
}

case "${1:-}" in
  "") ;;
  --remote)
    [[ $# -eq 2 ]] || { usage >&2; exit 2; }
    REMOTE="$2"
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

if [[ -z "$REMOTE" ]]; then
  sudo mkdir -p "$DEST/maps/routes"
  echo "Deploying validated OpenRoadCode map data to $DEST"
  sudo rsync "${RSYNC_OPTIONS[@]}" "$SOURCE" "$DEST"
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
fi

echo "Deployment complete. Runtime routes in ${DEST}maps/routes/ were preserved."
