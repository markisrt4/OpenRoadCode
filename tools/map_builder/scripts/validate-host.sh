#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONTAINER_ENGINE="${CONTAINER_ENGINE:-docker}"

if ! command -v "$CONTAINER_ENGINE" >/dev/null 2>&1; then
  echo "Container engine not found: $CONTAINER_ENGINE" >&2
  exit 1
fi

mkdir -p "$ROOT/build-output" "$ROOT/.cache" "$ROOT/.scratch"
exec "$CONTAINER_ENGINE" run --rm -it --network host --mount "type=bind,src=$ROOT/build-output,dst=/srv/openroadcode" --mount "type=bind,src=$ROOT/.cache,dst=/cache" --mount "type=bind,src=$ROOT/.scratch,dst=/scratch" openroadcode-map-builder:local validate --service-smoke
