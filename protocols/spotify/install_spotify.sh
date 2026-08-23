#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
SETUP_SCRIPT="$PROJECT_ROOT/controllers/spotify/install_spotify.sh"
SECRETS_FILE="${SECRETS_FILE:-${HOME}/.config/openroadcode/secrets.env}"
PYTHON_BIN="${PYTHON_BIN:-$PROJECT_ROOT/venv/bin/python}"

if [[ ! -x "$PYTHON_BIN" ]]; then
    echo "Python executable not found: $PYTHON_BIN" >&2
    echo "Set PYTHON_BIN or create the project virtual environment first." >&2
    exit 1
fi

"$SETUP_SCRIPT" --secrets-file "$SECRETS_FILE" "$@"

echo
echo "Starting Spotify authorization..."
cd "$PROJECT_ROOT"
"$PYTHON_BIN" -m protocols.spotify.component_test.spotify_auth_cli \
    --secrets-file "$SECRETS_FILE"
