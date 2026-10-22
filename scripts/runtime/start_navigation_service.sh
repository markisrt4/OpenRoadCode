#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
PYTHON_BIN="${OPENROADCODE_PYTHON:-$PROJECT_ROOT/venv/bin/python}"
RUNTIME_CONFIG="${OPENROADCODE_RUNTIME_CONFIG:-$PROJECT_ROOT/config/runtime.toml}"
SERVICE_NAME="openroadcode-navigation.service"
SERVICE_STOPPED=false

if [[ ! -x "$PYTHON_BIN" ]]; then
    PYTHON_BIN="python3"
fi

service_control() {
    local action="$1"
    if [[ -n "${OPENROADCODE_SERVICE_CONTROL:-}" ]]; then
        "$OPENROADCODE_SERVICE_CONTROL" "$action" "$SERVICE_NAME"
    elif [[ $EUID -eq 0 ]]; then
        systemctl "$action" "$SERVICE_NAME"
    elif command -v sudo >/dev/null 2>&1; then
        sudo systemctl "$action" "$SERVICE_NAME"
    else
        echo "Cannot $action $SERVICE_NAME: root privileges are required." >&2
        return 1
    fi
}

restore_installed_service() {
    local status=$?
    trap - EXIT INT TERM
    if [[ "$SERVICE_STOPPED" == true ]]; then
        echo "Restoring installed $SERVICE_NAME..."
        if ! service_control start; then
            echo "Failed to restart $SERVICE_NAME; restart it manually." >&2
            status=1
        fi
    fi
    exit "$status"
}

# systemd invokes this same wrapper for the installed unit. Only an explicit
# foreground launch may hand ownership away from an already active unit.
if [[ "${OPENROADCODE_INSTALLED_SERVICE:-0}" != 1 ]] \
        && command -v systemctl >/dev/null 2>&1 \
        && systemctl is-active --quiet "$SERVICE_NAME"; then
    echo "Temporarily stopping installed $SERVICE_NAME for foreground navigation..."
    if ! service_control stop; then
        echo "Unable to stop $SERVICE_NAME; its command and location ports remain owned." >&2
        exit 1
    fi
    SERVICE_STOPPED=true
    trap restore_installed_service EXIT
    trap 'exit 130' INT
    trap 'exit 143' TERM
fi

cd "$PROJECT_ROOT"
if [[ "$SERVICE_STOPPED" == false ]]; then
    exec "$PYTHON_BIN" -m services.navigation.navigation_service_cli \
        --config "$RUNTIME_CONFIG" "$@"
fi

set +e
"$PYTHON_BIN" -m services.navigation.navigation_service_cli \
    --config "$RUNTIME_CONFIG" "$@"
status=$?
exit "$status"
