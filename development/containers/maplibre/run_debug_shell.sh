#!/usr/bin/env bash
set -euo pipefail

CONTAINER_ENGINE="${CONTAINER_ENGINE:-docker}"
IMAGE_NAME="${IMAGE_NAME:-openroadcode-maplibre-builder}"
HOST_SRC="${HOST_SRC:-$HOME/src}"

MAPLIBRE_REPO="${MAPLIBRE_REPO:-https://github.com/maplibre/maplibre-native.git}"
MAPLIBRE_DIR="${MAPLIBRE_DIR:-maplibre-native}"

if ! command -v "$CONTAINER_ENGINE" >/dev/null 2>&1; then
    echo "Container engine not found: $CONTAINER_ENGINE" >&2
    exit 1
fi

if [[ ! -d "$HOST_SRC" ]]; then
    echo "Host source directory not found: $HOST_SRC" >&2
    exit 1
fi

echo "Starting debug shell using $CONTAINER_ENGINE..."
echo "Mounting: $HOST_SRC -> /src"

"$CONTAINER_ENGINE" run \
    --rm \
    --interactive \
    --tty \
    --volume "$HOST_SRC:/src" \
    --workdir /src \
    "$IMAGE_NAME" \
    /bin/bash -lc "
        set -e

        if [[ ! -d '/src/$MAPLIBRE_DIR/.git' ]]; then
            echo 'MapLibre Native not found. Cloning...'

            git clone \
                --recurse-submodules \
                '$MAPLIBRE_REPO' \
                '/src/$MAPLIBRE_DIR'
        else
            echo 'MapLibre Native already exists at /src/$MAPLIBRE_DIR'
        fi

        exec /bin/bash
    "

