#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
PYTHON_BIN="${OPENROADCODE_PYTHON:-python3}"

cd "$PROJECT_ROOT"

ARGS=()
if [[ -n "${OPENROADCODE_ZMQ_PUBLISHER_BIND_ENDPOINT:-}" ]]; then
    ARGS+=(--publisher-endpoint "$OPENROADCODE_ZMQ_PUBLISHER_BIND_ENDPOINT")
fi
if [[ -n "${OPENROADCODE_ZMQ_SUBSCRIBER_BIND_ENDPOINT:-}" ]]; then
    ARGS+=(--subscriber-endpoint "$OPENROADCODE_ZMQ_SUBSCRIBER_BIND_ENDPOINT")
fi

exec "$PYTHON_BIN" -m messaging.zeromq.broker_cli "${ARGS[@]}" "$@"
