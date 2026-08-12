#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONTAINER_ENGINE="${CONTAINER_ENGINE:-docker}"

if ! command -v "$CONTAINER_ENGINE" >/dev/null 2>&1; then
  echo "Container engine not found: $CONTAINER_ENGINE" >&2
  exit 1
fi

source "$ROOT/toolchain.lock"
"$CONTAINER_ENGINE" build \
  --build-arg "DEBIAN_BASE=$DEBIAN_BASE" \
  --build-arg "TILEMAKER_COMMIT=$TILEMAKER_COMMIT" \
  --build-arg "VALHALLA_COMMIT=$VALHALLA_COMMIT" \
  --build-arg "GLYPHS_COMMIT=$GLYPHS_COMMIT" \
  -t openroadcode-map-builder:local \
  "$ROOT"
