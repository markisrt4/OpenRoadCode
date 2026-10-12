#!/data/data/com.termux/files/usr/bin/bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

DEFAULT_REDIRECT_URI="http://127.0.0.1:8888/callback"
CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"
SECRETS_FILE="${SECRETS_FILE:-${CONFIG_HOME}/openroadcode/secrets.env}"

usage() {
    cat <<EOF
Usage: $(basename "$0") [--client-id ID] [--redirect-uri URI]
                            [--secrets-file PATH]

Configure Spotify credentials for OpenRoadCode on Termux.

Spotify uses OAuth PKCE, so a client secret is not required. Create an app at
the Spotify Developer Dashboard and provide its Client ID.

Options:
  --client-id ID       Spotify application Client ID
  --redirect-uri URI   OAuth callback URI (default: ${DEFAULT_REDIRECT_URI})
  --secrets-file PATH  Environment file (default: ${SECRETS_FILE})
  -h, --help           Show this help
EOF
}

fail() {
    echo "Error: $*" >&2
    exit 1
}

client_id=""
redirect_uri="${DEFAULT_REDIRECT_URI}"

while (( $# > 0 )); do
    case "$1" in
        --client-id)
            (( $# >= 2 )) || fail "--client-id requires a value"
            client_id="$2"
            shift 2
            ;;
        --redirect-uri)
            (( $# >= 2 )) || fail "--redirect-uri requires a value"
            redirect_uri="$2"
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

secrets_dir="$(dirname -- "$SECRETS_FILE")"
mkdir -p -- "$secrets_dir"
chmod 0700 "$secrets_dir"

[[ -w "$secrets_dir" ]] || fail "secrets directory is not writable: $secrets_dir"

echo
echo "Spotify Setup (Termux)"
echo "======================="
echo
echo "Create an application in the Spotify Developer Dashboard and register:"
echo "  ${redirect_uri}"
echo
echo "Spotify uses OAuth PKCE; no client secret is needed."
echo

while [[ -z "$client_id" ]]; do
    read -r -p "Spotify Client ID: " client_id
    client_id="${client_id//[[:space:]]/}"
done

[[ "$client_id" =~ ^[A-Za-z0-9._~-]+$ ]] \
    || fail "the Client ID contains unsupported characters"
[[ "$redirect_uri" != *[$'\r\n\t ']* ]] \
    || fail "the redirect URI cannot contain whitespace"
[[ "$redirect_uri" != *['"\']* ]] \
    || fail "the redirect URI cannot contain quotes or backslashes"

touch -- "$SECRETS_FILE"
chmod 0600 "$SECRETS_FILE"

temporary_file="$(mktemp "${secrets_dir}/.spotify-secrets.XXXXXX")"
cleanup() {
    rm -f -- "$temporary_file"
}
trap cleanup EXIT

awk '
    !/^SPOTIFY_CLIENT_ID=/ &&
    !/^SPOTIFY_REDIRECT_URI=/
' "$SECRETS_FILE" > "$temporary_file"

printf 'SPOTIFY_CLIENT_ID=%s\n' "$client_id" >> "$temporary_file"
printf 'SPOTIFY_REDIRECT_URI=%s\n' "$redirect_uri" >> "$temporary_file"

chmod 0600 "$temporary_file"
mv -f -- "$temporary_file" "$SECRETS_FILE"
trap - EXIT

echo
echo "Spotify configuration written to:"
echo "  ${SECRETS_FILE}"
echo
echo "Restart OpenRoadCode to load the new credentials."
