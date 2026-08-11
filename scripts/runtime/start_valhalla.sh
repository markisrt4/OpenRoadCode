#!/usr/bin/env bash
set -euo pipefail

VALHALLA_CONFIG="${VALHALLA_CONFIG:-/opt/valhalla/valhalla.json}"
VALHALLA_WORKERS="${VALHALLA_WORKERS:-1}"

if ! command -v valhalla_service >/dev/null 2>&1; then
    echo "valhalla_service is not available in PATH." >&2
    exit 1
fi

if [[ ! -f "$VALHALLA_CONFIG" ]]; then
    echo "Valhalla configuration not found: $VALHALLA_CONFIG" >&2
    exit 1
fi

exec valhalla_service \
    "$VALHALLA_CONFIG" \
    "$VALHALLA_WORKERS"

