#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

OPENROADCODE_SRC="${OPENROADCODE_SRC:-/src/OpenRoadCode}"
MAPLIBRE_SRC="${MAPLIBRE_SRC:-/src/maplibre-native}"
MAPLIBRE_BUILD="${MAPLIBRE_BUILD:-$MAPLIBRE_SRC/build-linux-opengl}"
RENDERER_BUILD_DIR="${RENDERER_BUILD_DIR:-$OPENROADCODE_SRC/apps/map_renderer/build-container}"
BUILD_JOBS="${BUILD_JOBS:-4}"

if [[ ! -f "$OPENROADCODE_SRC/apps/map_renderer/CMakeLists.txt" ]]; then
    echo "OpenRoadCode source not found: $OPENROADCODE_SRC" >&2
    exit 1
fi

if [[ ! -f "$MAPLIBRE_BUILD/libmbgl-core.a" ]]; then
    echo "MapLibre build not found: $MAPLIBRE_BUILD" >&2
    echo "Run build_maplibre.sh first." >&2
    exit 1
fi

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

echo "Map renderer built at:"
echo "  $RENDERER_BUILD_DIR/openroadcode-map-renderer"

