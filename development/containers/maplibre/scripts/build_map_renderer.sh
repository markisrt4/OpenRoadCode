#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_OPENROADCODE_SRC="$(cd -- "$SCRIPT_DIR/../../../.." && pwd)"

OPENROADCODE_SRC="${OPENROADCODE_SRC:-$DEFAULT_OPENROADCODE_SRC}"

SOURCE_ROOT="$(dirname -- "$OPENROADCODE_SRC")"
MAPLIBRE_SRC="${MAPLIBRE_SRC:-$SOURCE_ROOT/maplibre-native}"

MAPLIBRE_BUILD="${MAPLIBRE_BUILD:-$MAPLIBRE_SRC/build-linux-opengl}"
RENDERER_BUILD_DIR="${RENDERER_BUILD_DIR:-$OPENROADCODE_SRC/apps/map_renderer/build-container}"
BUILD_JOBS="${BUILD_JOBS:-4}"

echo "OpenRoadCode source:"
echo "  $OPENROADCODE_SRC"
echo
echo "MapLibre source:"
echo "  $MAPLIBRE_SRC"
echo
echo "MapLibre build:"
echo "  $MAPLIBRE_BUILD"
echo
echo "Renderer build:"
echo "  $RENDERER_BUILD_DIR"
echo

if [[ ! -f "$OPENROADCODE_SRC/apps/map_renderer/CMakeLists.txt" ]]; then
    echo "ERROR: OpenRoadCode source not found:" >&2
    echo "  $OPENROADCODE_SRC" >&2
    exit 1
fi

if [[ ! -d "$MAPLIBRE_SRC" ]]; then
    echo "ERROR: MapLibre source not found:" >&2
    echo "  $MAPLIBRE_SRC" >&2
    exit 1
fi

if [[ ! -f "$MAPLIBRE_BUILD/libmbgl-core.a" ]]; then
    echo "ERROR: MapLibre build not found:" >&2
    echo "  $MAPLIBRE_BUILD" >&2
    echo >&2
    echo "Run build_maplibre.sh first." >&2
    exit 1
fi

mkdir -p "$RENDERER_BUILD_DIR"

cmake \
    -S "$OPENROADCODE_SRC/apps/map_renderer" \
    -B "$RENDERER_BUILD_DIR" \
    -G Ninja \
    -DCMAKE_BUILD_TYPE=Release \
    -DMAPLIBRE_ROOT="$MAPLIBRE_SRC" \
    -DMAPLIBRE_BUILD="$MAPLIBRE_BUILD"

cmake --build "$RENDERER_BUILD_DIR" \
    --target openroadcode-map-renderer \
    -j"$BUILD_JOBS"

echo
echo "Map renderer built successfully:"
echo "  $RENDERER_BUILD_DIR/openroadcode-map-renderer"
