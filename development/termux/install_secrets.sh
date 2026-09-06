#!/data/data/com.termux/files/usr/bin/bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"
SECRETS_FILE="${SECRETS_FILE:-${CONFIG_HOME}/openroadcode/secrets.env}"

declare -A UPDATES=()

usage() {
    cat <<EOF
Usage: $(basename "$0") [options]

Configure OpenRoadCode secrets on Termux while preserving unrelated entries.

Options:
  --youtube-api-key KEY      Set YOUTUBE_API_KEY
  --spotify-client-id ID     Set SPOTIFY_CLIENT_ID
  --spotify-redirect-uri URI Set SPOTIFY_REDIRECT_URI
  --secrets-file PATH        Override secrets file path
  -h, --help                 Show this help

If a supported value is omitted, the script will prompt for it only when no
other secret option was supplied.
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

case "${PREFIX:-}" in
    */com.termux/files/usr) ;;
    *) fail "this installer is intended for Termux; PREFIX=${PREFIX:-<unset>}" ;;
esac

if (( ${#UPDATES[@]} == 0 )); then
    echo
    echo "OpenRoadCode Secrets Setup (Termux)"
    echo "==================================="
    echo
    read -r -p "YouTube Data API key: " youtube_api_key
    youtube_api_key="${youtube_api_key//[[:space:]]/}"
    [[ -n "$youtube_api_key" ]] || fail "YouTube API key cannot be empty"
    set_update "YOUTUBE_API_KEY" "$youtube_api_key"
fi

secrets_dir="$(dirname -- "$SECRETS_FILE")"
mkdir -p -- "$secrets_dir"
chmod 0700 "$secrets_dir"
[[ -w "$secrets_dir" ]] || fail "secrets directory is not writable: $secrets_dir"

touch -- "$SECRETS_FILE"
chmod 0600 "$SECRETS_FILE"

temporary_file="$(mktemp "${secrets_dir}/.orc-secrets.XXXXXX")"
cleanup() {
    rm -f -- "$temporary_file"
}
trap cleanup EXIT

# Preserve comments, blank lines, and unrelated secrets. Replace only keys
# explicitly supplied to this invocation.
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
' "$SECRETS_FILE" > "$temporary_file"

for name in "${!UPDATES[@]}"; do
    value="${UPDATES[$name]}"
    [[ -n "$value" ]] || fail "$name cannot be empty"
    printf '%s=%s\n' "$name" "$value" >> "$temporary_file"
done

chmod 0600 "$temporary_file"
mv -f -- "$temporary_file" "$SECRETS_FILE"
trap - EXIT

echo
echo "Updated OpenRoadCode secrets:"
for name in "${!UPDATES[@]}"; do
    echo "  $name"
done
echo
echo "Secrets file:"
echo "  $SECRETS_FILE"
echo
echo "Restart OpenRoadCode to load the new values."
