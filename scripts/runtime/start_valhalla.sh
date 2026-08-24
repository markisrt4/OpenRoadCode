#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

VALHALLA_CONFIG="${VALHALLA_CONFIG:-/srv/openroadcode/valhalla/valhalla.json}"
VALHALLA_WORKERS="${VALHALLA_WORKERS:-1}"
VALHALLA_BIN="${VALHALLA_BIN:-/opt/openroadcode/navigation/valhalla/bin/valhalla_service}"

if [[ ! -x "$VALHALLA_BIN" ]]; then
    echo "Valhalla service executable not found: $VALHALLA_BIN" >&2
    exit 1
fi

if [[ ! -f "$VALHALLA_CONFIG" ]]; then
    echo "Valhalla configuration not found: $VALHALLA_CONFIG" >&2
    exit 1
fi

exec "$VALHALLA_BIN" \
    "$VALHALLA_CONFIG" \
    "$VALHALLA_WORKERS"
