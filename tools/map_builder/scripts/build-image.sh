#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/toolchain.lock"
docker build --build-arg "DEBIAN_BASE=$DEBIAN_BASE" --build-arg "TILEMAKER_COMMIT=$TILEMAKER_COMMIT" --build-arg "VALHALLA_COMMIT=$VALHALLA_COMMIT" --build-arg "GLYPHS_COMMIT=$GLYPHS_COMMIT" -t openroadcode-map-builder:local "$ROOT"
