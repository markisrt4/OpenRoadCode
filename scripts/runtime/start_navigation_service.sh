#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
PYTHON_BIN="${OPENROADCODE_PYTHON:-$PROJECT_ROOT/venv/bin/python}"
RUNTIME_CONFIG="${OPENROADCODE_RUNTIME_CONFIG:-$PROJECT_ROOT/config/runtime.toml}"

if [[ ! -x "$PYTHON_BIN" ]]; then
    PYTHON_BIN="python3"
fi

cd "$PROJECT_ROOT"
exec "$PYTHON_BIN" -m services.navigation.navigation_service_cli \
    --config "$RUNTIME_CONFIG" "$@"
