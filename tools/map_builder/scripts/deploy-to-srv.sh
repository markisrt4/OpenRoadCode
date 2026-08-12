#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE="$ROOT/build-output/"
DEST="/srv/openroadcode/"
[[ -f "$ROOT/build-output/build-manifest.json" ]] || { echo "No validated build-output/build-manifest.json found. Build first." >&2; exit 2; }
sudo mkdir -p "$DEST"
echo "Deploying validated OpenRoadCode map data to $DEST"
sudo rsync -a --delete --exclude 'maps/routes/' "$SOURCE" "$DEST"
sudo mkdir -p "$DEST/maps/routes"
echo "Deployment complete."
