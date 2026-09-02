#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

# Standalone developer entry point for the native OpenRoadCode map renderer.
# The normal ORC UI owns the renderer process and supplies its parent X11
# window. This script deliberately omits that parent so the renderer opens in
# its own Termux:X11 window for development and diagnostics.

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

export DISPLAY="${DISPLAY:-:1}"
export OPENROADCODE_DATA_ROOT="${OPENROADCODE_DATA_ROOT:-$HOME/.local/share/openroadcode}"
export OPENROADCODE_CACHE_ROOT="${OPENROADCODE_CACHE_ROOT:-$HOME/.cache/openroadcode}"
export OPENROADCODE_NAVIGATION_CONFIG="${OPENROADCODE_NAVIGATION_CONFIG:-$HOME/.local/state/openroadcode/navigation/navigation.termux.toml}"

exec bash "$SCRIPT_DIR/start_map_renderer.sh"
