#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

SECRETS_FILE="${SECRETS_FILE:-/etc/openroadcode/secrets.env}"
INSTALL_OWNER="$(id -un)"
INSTALL_GROUP="$(id -gn)"
declare -A UPDATES=()

usage() {
    cat <<EOF
Usage: $(basename "$0") [options]

Configure OpenRoadCode secrets on Debian/Linux while preserving unrelated entries.

Options:
  --youtube-api-key KEY      Set YOUTUBE_API_KEY
  --spotify-client-id ID     Set SPOTIFY_CLIENT_ID
  --spotify-redirect-uri URI Set SPOTIFY_REDIRECT_URI
  --secrets-file PATH        Override secrets file path
  -h, --help                 Show this help

With no secret options, the script prompts for Spotify configuration suitable
for the ORC Spotify controller/Web Playback SDK test.
EOF
}

fail() {
    echo "Error: $*" >&2
    exit 1
}

set_update() {
    local name="$1"
    local value="$2"
    [[ "$value" != *$'\n'* && "$value" != *$'\r'* ]] \
        || fail "$name cannot contain newlines"
    [[ -n "$value" ]] || fail "$name cannot be empty"
    UPDATES["$name"]="$value"
}

while (( $# > 0 )); do
    case "$1" in
        --youtube-api-key)
            (( $# >= 2 )) || fail "--youtube-api-key requires a value"
            set_update "YOUTUBE_API_KEY" "$2"
            shift 2
            ;;
        --spotify-client-id)
            (( $# >= 2 )) || fail "--spotify-client-id requires a value"
            set_update "SPOTIFY_CLIENT_ID" "$2"
            shift 2
            ;;
        --spotify-redirect-uri)
            (( $# >= 2 )) || fail "--spotify-redirect-uri requires a value"
            set_update "SPOTIFY_REDIRECT_URI" "$2"
            shift 2
            ;;
        --secrets-file)
            (( $# >= 2 )) || fail "--secrets-file requires a path"
            SECRETS_FILE="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            fail "unknown argument: $1"
            ;;
    esac
done

if (( ${#UPDATES[@]} == 0 )); then
    echo
    echo "OpenRoadCode Secrets Setup (Debian/Linux)"
    echo "========================================="
    echo
    read -r -p "Spotify client ID: " spotify_client_id
    spotify_client_id="${spotify_client_id//[[:space:]]/}"
    set_update "SPOTIFY_CLIENT_ID" "$spotify_client_id"

    read -r -p "Spotify redirect URI [http://127.0.0.1:8888/callback]: " spotify_redirect_uri
    spotify_redirect_uri="${spotify_redirect_uri:-http://127.0.0.1:8888/callback}"
    set_update "SPOTIFY_REDIRECT_URI" "$spotify_redirect_uri"
fi

secrets_dir="$(dirname -- "$SECRETS_FILE")"
temporary_file="$(mktemp)"
filtered_file="$(mktemp)"
cleanup() {
    rm -f -- "$temporary_file" "$filtered_file"
}
trap cleanup EXIT

if [[ -r "$SECRETS_FILE" ]]; then
    cat -- "$SECRETS_FILE" > "$temporary_file"
elif command -v sudo >/dev/null 2>&1 && sudo test -r "$SECRETS_FILE" 2>/dev/null; then
    sudo cat -- "$SECRETS_FILE" > "$temporary_file"
fi

awk -v keys="$(printf '%s\n' "${!UPDATES[@]}")" '
    BEGIN {
        n = split(keys, entries, "\n")
        for (i = 1; i <= n; ++i) {
            if (entries[i] != "") wanted[entries[i]] = 1
        }
    }
    {
        line = $0
        normalized = line
        sub(/^[[:space:]]*export[[:space:]]+/, "", normalized)
        split(normalized, parts, "=")
        name = parts[1]
        gsub(/^[[:space:]]+|[[:space:]]+$/, "", name)
        if (name in wanted) next
        print line
    }
' "$temporary_file" > "$filtered_file"

for name in "${!UPDATES[@]}"; do
    printf '%s=%s\n' "$name" "${UPDATES[$name]}" >> "$filtered_file"
done

if [[ "$SECRETS_FILE" == /etc/* ]]; then
    command -v sudo >/dev/null 2>&1 || fail "sudo is required to write $SECRETS_FILE"
    sudo install -d -m 0755 -- "$secrets_dir"
    sudo install -o "$INSTALL_OWNER" -g "$INSTALL_GROUP" -m 0600 \
        -- "$filtered_file" "$SECRETS_FILE"
else
    mkdir -p -- "$secrets_dir"
    chmod 0700 "$secrets_dir"
    install -m 0600 -- "$filtered_file" "$SECRETS_FILE"
fi

[[ -r "$SECRETS_FILE" ]] \
    || fail "installed secrets file is not readable by $INSTALL_OWNER: $SECRETS_FILE"

trap - EXIT
rm -f -- "$temporary_file" "$filtered_file"

echo
echo "Updated OpenRoadCode secrets:"
for name in "${!UPDATES[@]}"; do
    echo "  $name"
done
echo
echo "Secrets file:"
echo "  $SECRETS_FILE"
echo "Owner: $INSTALL_OWNER:$INSTALL_GROUP (mode 0600)"
echo
echo "Restart OpenRoadCode to load the new values."
