#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
PYTHON_BIN="${OPENROADCODE_PYTHON:-python3}"

cd "$PROJECT_ROOT"

ARGS=()
if [[ "${OPENROADCODE_NAV_SIMULATE:-0}" == "1" ]]; then
    ARGS+=(--simulate)
fi
if [[ "${OPENROADCODE_NAV_GPS:-0}" == "1" ]]; then
    ARGS+=(--gps)
fi
if [[ -n "${OPENROADCODE_NAV_RATE_HZ:-}" ]]; then
    ARGS+=(--rate-hz "$OPENROADCODE_NAV_RATE_HZ")
fi
if [[ -n "${OPENROADCODE_NAV_COMMAND_ENDPOINT:-}" ]]; then
    ARGS+=(--command-endpoint "$OPENROADCODE_NAV_COMMAND_ENDPOINT")
fi
if [[ -n "${OPENROADCODE_NAV_PUBLISHER_ENDPOINT:-}" ]]; then
    ARGS+=(--publisher-endpoint "$OPENROADCODE_NAV_PUBLISHER_ENDPOINT")
fi

exec "$PYTHON_BIN" -m services.navigation.navigation_service_cli "${ARGS[@]}" "$@"
