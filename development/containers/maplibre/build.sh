#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

CONTAINER_ENGINE="${CONTAINER_ENGINE:-docker}"
IMAGE_NAME="${IMAGE_NAME:-openroadcode-maplibre-builder}"
BASE_IMAGE="${BASE_IMAGE:-debian:trixie}"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

if ! command -v "$CONTAINER_ENGINE" >/dev/null 2>&1; then
    echo "Container engine not found: $CONTAINER_ENGINE" >&2
    exit 1
fi

echo "Building $IMAGE_NAME using $CONTAINER_ENGINE (base: $BASE_IMAGE)..."

"$CONTAINER_ENGINE" build \
    --build-arg "BASE_IMAGE=$BASE_IMAGE" \
    --tag "$IMAGE_NAME" \
    "$SCRIPT_DIR"

echo "Built container image: $IMAGE_NAME"
