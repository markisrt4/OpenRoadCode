#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

DEFAULT_REDIRECT_URI="http://127.0.0.1:8888/callback"
SECRETS_FILE="${SECRETS_FILE:-${HOME}/.config/openroadcode/secrets.env}"

usage() {
    cat <<EOF
Usage: $(basename "$0") [--client-id ID] [--redirect-uri URI]
                            [--secrets-file PATH]

Configure Spotify credentials for OpenRoadCode.

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
service_user="${SERVICE_USER:-${SUDO_USER:-${USER:-}}}"
[[ -n "$service_user" ]] || fail "unable to determine the service user"
service_group="$(id -g "$service_user")" \
    || fail "service user does not exist: $service_user"

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

secrets_dir="$(dirname -- "$SECRETS_FILE")"
permission_path="$SECRETS_FILE"
if [[ ! -e "$permission_path" ]]; then
    permission_path="$secrets_dir"
    while [[ ! -e "$permission_path" ]]; do
        parent_path="$(dirname -- "$permission_path")"
        [[ "$parent_path" != "$permission_path" ]] || break
        permission_path="$parent_path"
    done
fi

if [[ $EUID -ne 0 && ! -w "$permission_path" ]]; then
    command -v sudo >/dev/null 2>&1 \
        || fail "root privileges are required and sudo is unavailable"

    args=(
        --redirect-uri "$redirect_uri"
        --secrets-file "$SECRETS_FILE"
    )
    if [[ -n "$client_id" ]]; then
        args+=(--client-id "$client_id")
    fi
    exec sudo -- "$0" "${args[@]}"
fi

echo
echo "Spotify Setup"
echo "============="
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

if [[ ! -d "$secrets_dir" ]]; then
    if [[ $EUID -eq 0 ]]; then
        install -d -m 0750 -o root -g "$service_group" "$secrets_dir"
    else
        install -d -m 0700 "$secrets_dir"
    fi
elif [[ $EUID -eq 0 && "$secrets_dir" == "/etc/openroadcode" ]]; then
    chown "root:$service_group" "$secrets_dir"
    chmod 0750 "$secrets_dir"
fi

if [[ ! -e "$SECRETS_FILE" ]]; then
    if [[ $EUID -eq 0 ]]; then
        install -m 0640 -o root -g "$service_group" \
            /dev/null "$SECRETS_FILE"
    else
        install -m 0600 /dev/null "$SECRETS_FILE"
    fi
elif [[ $EUID -eq 0 ]]; then
    chown "root:$service_group" "$SECRETS_FILE"
    chmod 0640 "$SECRETS_FILE"
fi

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

owner="$(stat -c '%u' "$SECRETS_FILE")"
group="$(stat -c '%g' "$SECRETS_FILE")"
chown "$owner:$group" "$temporary_file"
chmod 0640 "$temporary_file"
mv -f -- "$temporary_file" "$SECRETS_FILE"
chmod 0600 "$SECRETS_FILE"
trap - EXIT

echo
echo "Spotify configuration written to:"
echo "  ${SECRETS_FILE}"
echo
echo "Restart OpenRoadCode to load it:"
echo "  sudo systemctl restart openroadcode.service"
