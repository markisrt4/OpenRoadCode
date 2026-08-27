#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

CONTAINER_ENGINE="${CONTAINER_ENGINE:-docker}"
IMAGE_NAME="${IMAGE_NAME:-openroadcode-maplibre-builder}"
HOST_SRC="${HOST_SRC:-$HOME/src}"

MAPLIBRE_REPO="${MAPLIBRE_REPO:-https://github.com/maplibre/maplibre-native.git}"
MAPLIBRE_DIR="${MAPLIBRE_DIR:-maplibre-native}"
MAPLIBRE_REF="${MAPLIBRE_REF:-b0388d186d582a8535aa3c03e3cc2ef98cb70dc0}"

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
                '$MAPLIBRE_REPO' \
                '/src/$MAPLIBRE_DIR'

            git -C '/src/$MAPLIBRE_DIR' \
                checkout --detach '$MAPLIBRE_REF'
        else
            echo 'MapLibre Native already exists at /src/$MAPLIBRE_DIR'
        fi

        cd '/src/$MAPLIBRE_DIR'

        if [[ \"\$(git rev-parse HEAD)\" != '$MAPLIBRE_REF' ]]; then
            echo 'MapLibre checkout does not match MAPLIBRE_REF.' >&2
            echo 'Expected: $MAPLIBRE_REF' >&2
            echo \"Actual:   \$(git rev-parse HEAD)\" >&2
            echo 'Use a clean checkout or explicitly set MAPLIBRE_REF.' >&2
            exit 1
        fi

        git submodule sync --recursive
        git submodule update --init --recursive

        exec /bin/bash
    "
