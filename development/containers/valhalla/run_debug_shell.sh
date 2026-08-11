#!/usr/bin/env bash
set -euo pipefail

CONTAINER_ENGINE="${CONTAINER_ENGINE:-docker}"
IMAGE_NAME="${IMAGE_NAME:-openroadcode-valhalla-builder}"
HOST_SRC="${HOST_SRC:-$HOME/src}"

VALHALLA_REPO="${VALHALLA_REPO:-https://github.com/valhalla/valhalla.git}"
VALHALLA_DIR="${VALHALLA_DIR:-valhalla}"

PRIME_SERVER_REPO="${PRIME_SERVER_REPO:-https://github.com/kevinkreiser/prime_server.git}"
PRIME_SERVER_DIR="${PRIME_SERVER_DIR:-prime_server}"

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

        if [[ ! -d '/src/$PRIME_SERVER_DIR/.git' ]]; then
            echo 'prime_server not found. Cloning...'

            git clone \
                --recurse-submodules \
                '$PRIME_SERVER_REPO' \
                '/src/$PRIME_SERVER_DIR'
        else
            echo 'prime_server already exists at /src/$PRIME_SERVER_DIR'
        fi

        if [[ ! -d '/src/$VALHALLA_DIR/.git' ]]; then
            echo 'Valhalla not found. Cloning...'

            git clone \
                --recurse-submodules \
                '$VALHALLA_REPO' \
                '/src/$VALHALLA_DIR'
        else
            echo 'Valhalla already exists at /src/$VALHALLA_DIR'
        fi

        exec /bin/bash
    "
