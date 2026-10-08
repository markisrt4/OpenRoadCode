#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
IS_TERMUX=false
if [[ -n "${TERMUX_VERSION:-}" || "${PREFIX:-}" == *com.termux* ]]; then
    IS_TERMUX=true
    : "${PREFIX:?Termux PREFIX is required}"
    VALHALLA_DATA_ROOT="${VALHALLA_DATA_ROOT:-${XDG_DATA_HOME:-$HOME/.local/share}/openroadcode/valhalla}"
    VALHALLA_CONFIG="${VALHALLA_CONFIG:-$VALHALLA_DATA_ROOT/valhalla.json}"
    VALHALLA_BIN="${VALHALLA_BIN:-$PREFIX/opt/openroadcode/navigation/valhalla/bin/valhalla_service}"
else
    VALHALLA_CONFIG="${VALHALLA_CONFIG:-/srv/openroadcode/valhalla/valhalla.json}"
    VALHALLA_BIN="${VALHALLA_BIN:-/opt/openroadcode/navigation/valhalla/bin/valhalla_service}"
fi
VALHALLA_WORKERS="${VALHALLA_WORKERS:-1}"

if [[ ! -x "$VALHALLA_BIN" ]]; then
    echo "Valhalla service executable not found: $VALHALLA_BIN" >&2
    exit 1
fi

if [[ ! -f "$VALHALLA_CONFIG" ]]; then
    echo "Valhalla configuration not found: $VALHALLA_CONFIG" >&2
    exit 1
fi

if "$IS_TERMUX"; then
    VALHALLA_RUNTIME_ROOT="${VALHALLA_RUNTIME_ROOT:-$PREFIX/tmp/openroadcode-valhalla}"
    PREPARED_CONFIG="$VALHALLA_RUNTIME_ROOT/valhalla.termux.json"
    "${OPENROADCODE_PYTHON:-python3}" "$SCRIPT_DIR/prepare_termux_valhalla.py" \
        --source "$VALHALLA_CONFIG" --destination "$PREPARED_CONFIG" \
        --data-root "$VALHALLA_DATA_ROOT" --runtime-root "$VALHALLA_RUNTIME_ROOT"
    VALHALLA_CONFIG="$PREPARED_CONFIG"
fi

exec "$VALHALLA_BIN" \
    "$VALHALLA_CONFIG" \
    "$VALHALLA_WORKERS"
