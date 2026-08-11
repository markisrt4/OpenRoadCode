#!/usr/bin/env bash
set -euo pipefail

CONTAINER_ENGINE="${CONTAINER_ENGINE:-docker}"
IMAGE_NAME="${IMAGE_NAME:-openroadcode-valhalla-builder}"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

if ! command -v "$CONTAINER_ENGINE" >/dev/null 2>&1; then
    echo "Container engine not found: $CONTAINER_ENGINE" >&2
    exit 1
fi

echo "Building $IMAGE_NAME using $CONTAINER_ENGINE..."

"$CONTAINER_ENGINE" build \
    --tag "$IMAGE_NAME" \
    "$SCRIPT_DIR"

echo "Built container image: $IMAGE_NAME"
