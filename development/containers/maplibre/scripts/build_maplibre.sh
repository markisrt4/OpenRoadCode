#!/usr/bin/env bash
set -euo pipefail

MAPLIBRE_SRC="${MAPLIBRE_SRC:-/src/maplibre-native}"
BUILD_DIR="${BUILD_DIR:-build-linux-opengl}"
BUILD_JOBS="${BUILD_JOBS:-4}"
BUILD_TARGET="${BUILD_TARGET:-mbgl-glfw}"

if [[ ! -d "$MAPLIBRE_SRC/.git" ]]; then
    echo "MapLibre Native source not found: $MAPLIBRE_SRC" >&2
    exit 1
fi

cd "$MAPLIBRE_SRC"

echo "MapLibre source: $MAPLIBRE_SRC"
echo "Build directory: $BUILD_DIR"
echo "Build target: $BUILD_TARGET"
echo "Parallel jobs: $BUILD_JOBS"

if [[ ! -d "$BUILD_DIR" ]]; then
    echo "Configuring MapLibre Native..."

    cmake --preset linux-opengl \
        -DCMAKE_C_COMPILER=gcc \
        -DCMAKE_CXX_COMPILER=g++
fi

echo "Building MapLibre Native..."

cmake --build "$BUILD_DIR" \
    --target "$BUILD_TARGET" \
    -j"$BUILD_JOBS"

echo "MapLibre build complete."

