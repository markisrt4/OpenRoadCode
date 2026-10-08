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

SEARCH_DB_REL="maps/search/openroadcode-search.sqlite"
LEGACY_POI_DB_REL="maps/poi/openroadcode-poi.sqlite"

if [[ ! -s "$SOURCE$SEARCH_DB_REL" && ! -s "$SOURCE$LEGACY_POI_DB_REL" ]]; then
  echo "Validated output is missing the POI search database." >&2
  echo "Expected $SEARCH_DB_REL (or legacy $LEGACY_POI_DB_REL)." >&2
  exit 2
fi

REPO_ROOT="$(cd -- "$ROOT/../.." && pwd)"

if [[ -s "$SOURCE$SEARCH_DB_REL" ]]; then
  SEARCH_DB="$SOURCE$SEARCH_DB_REL"
else
  SEARCH_DB="$SOURCE$LEGACY_POI_DB_REL"
fi

echo "Verifying build manifest matches deployable artifacts"
PYTHONPATH="$REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}" \
python3 - "$SOURCE" <<'PYMANIFEST'
import json
from pathlib import Path
import sys

from tools.map_builder.builder.validate import validate_output

root = Path(sys.argv[1])
manifest_path = root / "build-manifest.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
if manifest.get("schema") != 2:
    raise SystemExit(
        f"Refusing deployment: expected manifest schema 2, got {manifest.get('schema')!r}"
    )

validation = validate_output(root, service_smoke=False)
recorded = manifest.get("validation") or {}
if recorded.get("source_pbfs") != validation["source_pbfs"]:
    raise SystemExit(
        "Refusing deployment: manifest source PBF count does not match current artifacts"
    )

recorded_checksums = recorded.get("checksums") or {}
current_checksums = validation.get("checksums") or {}
for name, checksum in current_checksums.items():
    if recorded_checksums.get(name) != checksum:
        raise SystemExit(
            f"Refusing deployment: manifest checksum for {name} does not match current artifact"
        )

print("Manifest matches current validated artifacts")
PYMANIFEST

echo "Validating POI search database schema"
PYTHONPATH="$REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}" \
python3 - "$SEARCH_DB" <<'PYVALIDATE'
from pathlib import Path
import sys

from tools.map_builder.builder.validate import validate_search_index

database = Path(sys.argv[1])
result = validate_search_index(database)

print(f"Validated search index: {database}")
print(f"POI columns: {', '.join(result['poi_columns'])}")
PYVALIDATE

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
  if [[ ! -s "$DEST$SEARCH_DB_REL" && -s "$DEST$LEGACY_POI_DB_REL" ]]; then
    echo "Installing legacy POI index at canonical runtime path"
    sudo mkdir -p "$DEST/maps/search"
    sudo install -m 0644 "$DEST$LEGACY_POI_DB_REL" "$DEST$SEARCH_DB_REL"
  fi
  sudo test -s "$DEST$SEARCH_DB_REL"
else
  echo "Checking remote deployment prerequisites on $REMOTE"
  # Paths are intentionally expanded locally before being sent to the remote host.
  # shellcheck disable=SC2029
  if ! ssh "$REMOTE" "command -v rsync >/dev/null && sudo -n mkdir -p '$DEST/maps/routes'"; then
    echo "Remote deployment requires rsync and passwordless sudo for $REMOTE." >&2
    exit 2
  fi
  echo "Deploying validated OpenRoadCode map data to $REMOTE:$DEST"
  rsync "${RSYNC_OPTIONS[@]}" \
    --rsync-path="sudo -n rsync" \
    "$SOURCE" \
    "$REMOTE:$DEST"
  # shellcheck disable=SC2029
  ssh "$REMOTE" "if [[ ! -s '$DEST$SEARCH_DB_REL' && -s '$DEST$LEGACY_POI_DB_REL' ]]; then sudo -n mkdir -p '$DEST/maps/search' && sudo -n install -m 0644 '$DEST$LEGACY_POI_DB_REL' '$DEST$SEARCH_DB_REL'; fi; sudo -n test -s '$DEST$SEARCH_DB_REL'"
fi

echo "Deployment complete. Runtime routes in ${DEST}maps/routes/ were preserved."
