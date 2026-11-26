#!/usr/bin/env bash
# SPDX-License-Identifier: MIT

set -euo pipefail

project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
service=musicforge-airplay-tunnel.service
key="$HOME/.ssh/id_ed25519_musicforge_tunnel"
config_home="${XDG_CONFIG_HOME:-$HOME/.config}"
[[ "$config_home" = /* ]] || config_home="$HOME/.config"
unit_dir="$config_home/systemd/user"
unit="$unit_dir/$service"

if (( $# < 2 || $# > 4 )); then
    echo "Usage: bash $0 USER@HOST SSH_PORT [VPS_API_PORT] [LOGIN_KEY]" >&2
    exit 2
fi
vps="$1"
ssh_port="$2"
api_port="${3:-8003}"
local_port=8003
if [[ ! "$vps" =~ ^[a-zA-Z0-9_][a-zA-Z0-9_.-]*@[a-zA-Z0-9][a-zA-Z0-9.-]*$ ]]; then
    echo "Enter a VPS SSH destination in user@hostname or user@IPv4 format." >&2
    exit 2
fi
for port in "$ssh_port" "$api_port"; do
    if [[ ! "$port" =~ ^[1-9][0-9]{0,4}$ ]] || (( port > 65535 )); then
        echo "SSH and API ports must be between 1 and 65535." >&2
        exit 2
    fi
done
login_options=()
if (( $# == 4 )) && [[ -n "$4" ]]; then
    if [[ ! -f "$4" ]]; then
        echo "Interactive SSH key not found: $4" >&2
        exit 1
    fi
    login_options=(-i "$4" -o IdentitiesOnly=yes)
fi

if (( EUID == 0 )); then
    echo "Run as the user who runs ORC, without sudo." >&2
    exit 1
fi
for program in ssh ssh-keygen systemctl ss curl python3; do
    command -v "$program" >/dev/null || { echo "Missing command: $program" >&2; exit 1; }
done
systemctl --user show-environment >/dev/null
if ! systemctl --user is-active --quiet "$service" &&
    [[ -n "$(ss -H -ltn "sport = :$local_port")" ]]; then
    echo "Local port $local_port is occupied. Close the manual tunnel if it owns the port." >&2
    exit 1
fi

unit_content="$(cat <<EOF
[Unit]
Description=MusicForge Airplay SSH tunnel

[Service]
ExecStart=/usr/bin/ssh -F /dev/null -NT -p $ssh_port -i %h/.ssh/id_ed25519_musicforge_tunnel -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=yes -o ExitOnForwardFailure=yes -o ConnectTimeout=10 -o ServerAliveInterval=20 -o ServerAliveCountMax=3 -L 127.0.0.1:$local_port:127.0.0.1:$api_port $vps
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
EOF
)"
replace_unit=0
if [[ -e "$unit" || -L "$unit" ]]; then
    if [[ -L "$unit" || ! -f "$unit" ]]; then
        echo "Review the existing tunnel unit at $unit before continuing." >&2
        exit 1
    fi
    if [[ "$(cat "$unit")" != "$unit_content" ]]; then
        read -r -p "Replace the existing tunnel service? A backup will be saved. [y/N] " answer
        [[ "$answer" = [yY] ]] || exit 1
        replace_unit=1
    fi
fi

url="http://127.0.0.1:$local_port"
if (( ! replace_unit )) && [[ -f "$unit" ]] &&
    systemctl --user is-active --quiet "$service" &&
    curl -fsS --max-time 3 "$url/health" >/dev/null 2>&1; then
    systemctl --user enable "$service"
    (cd "$project_root" && python3 -m scripts.installers.setup_musicforge_airplay "$url")
    exit 0
fi

umask 077
mkdir -p "$HOME/.ssh" "$unit_dir"
if [[ ! -f "$key" ]]; then
    if [[ -e "$key" || -L "$key" || -e "$key.pub" || -L "$key.pub" ]]; then
        echo "Existing tunnel key files are incomplete. Review $key and $key.pub." >&2
        exit 1
    fi
    ssh-keygen -q -t ed25519 -N '' -f "$key" -C orc-airplay-tunnel
fi
chmod 600 "$key"
if ! public_key="$(ssh-keygen -y -P '' -f "$key")"; then
    echo "The tunnel key must be readable without a passphrase: $key" >&2
    exit 1
fi
read -r key_type key_blob _ <<<"$public_key"
if [[ "$key_type" != ssh-ed25519 || -z "$key_blob" ]]; then
    echo "Expected a dedicated Ed25519 tunnel key: $key" >&2
    exit 1
fi

echo "Signing in to the VPS once to authorize the tunnel key."
printf 'restrict,port-forwarding,permitopen="127.0.0.1:%s",command="/bin/false" %s %s orc-airplay-tunnel\n' \
    "$api_port" "$key_type" "$key_blob" |
    ssh -F /dev/null "${login_options[@]}" -o StrictHostKeyChecking=ask -p "$ssh_port" "$vps" '
        set -eu
        umask 077
        mkdir -p "$HOME/.ssh"
        IFS= read -r entry
        authorized="$HOME/.ssh/authorized_keys"
        touch "$authorized"
        chmod 600 "$authorized"
        set -- $entry
        existing="$(grep -F -- "$3" "$authorized" || true)"
        if [ "$existing" = "$entry" ]; then exit 0; fi
        if [ -n "$existing" ]; then
            echo "Tunnel key already exists with different options. Review authorized_keys." >&2
            exit 1
        fi
        printf "%s\n" "$entry" >> "$authorized"
    '

if (( replace_unit )); then
    backup="$(mktemp "$unit.backup.XXXXXX")"
    cp -- "$unit" "$backup"
    temporary="$(mktemp "$unit.XXXXXX")"
    printf '%s\n' "$unit_content" > "$temporary"
    mv -- "$temporary" "$unit"
elif [[ ! -e "$unit" ]]; then
    (set -C; printf '%s\n' "$unit_content" > "$unit")
fi
systemctl --user daemon-reload
systemctl --user enable --now "$service"
if (( replace_unit )); then
    systemctl --user restart "$service"
fi

for (( attempt=1; attempt<=8; attempt++ )); do
    if health="$(curl -fsS --max-time 3 "$url/health" 2>/dev/null)" &&
        curl -fsS --max-time 3 "$url/api/v1/stations" >/dev/null 2>&1; then
        printf 'Airplay API response: %s\n' "$health"
        (cd "$project_root" && python3 -m scripts.installers.setup_musicforge_airplay "$url")
        exit 0
    fi
    sleep 1
done
echo "Airplay did not respond via the tunnel. Check the VPS API and this journal:" >&2
journalctl --user -u "$service" -n 12 --no-pager >&2
exit 1
