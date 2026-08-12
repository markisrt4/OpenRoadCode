#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
SETUP_SCRIPT="$PROJECT_ROOT/controllers/spotify/install_spotify.sh"
SECRETS_FILE="${SECRETS_FILE:-/etc/openroadcode/secrets.env}"

"$SETUP_SCRIPT" --secrets-file "$SECRETS_FILE" "$@"

echo
echo "Starting Spotify authorization..."
cd "$PROJECT_ROOT"
python3 -m protocols.spotify.component_test.spotify_auth_cli \
    --secrets-file "$SECRETS_FILE"
