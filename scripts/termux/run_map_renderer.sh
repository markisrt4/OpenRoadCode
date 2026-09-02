#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"

export DISPLAY="${DISPLAY:-:1}"
export OPENROADCODE_DATA_ROOT="${OPENROADCODE_DATA_ROOT:-$HOME/.local/share/openroadcode}"
export OPENROADCODE_CACHE_ROOT="${OPENROADCODE_CACHE_ROOT:-$HOME/.cache/openroadcode}"
export OPENROADCODE_NAVIGATION_CONFIG="${OPENROADCODE_NAVIGATION_CONFIG:-$HOME/.local/state/openroadcode/navigation/navigation.termux.toml}"

exec "$REPO_ROOT/development/termux/start_map_renderer.sh"
