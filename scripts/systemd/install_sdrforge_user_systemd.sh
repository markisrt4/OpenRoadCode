#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
set -euo pipefail

if (( EUID == 0 )); then
  echo "Run as the intended desktop user, not root." >&2
  exit 1
fi
python_bin="${OPENROADCODE_PYTHON:?Set OPENROADCODE_PYTHON to the installed virtualenv Python}"
"$python_bin" -m sdrforge.live_transport_server --help >/dev/null
unit_dir="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
mkdir -p "$unit_dir"
sudo loginctl enable-linger "$(id -un)"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
export DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-unix:path=$XDG_RUNTIME_DIR/bus}"
cat > "$unit_dir/libsdrforge.service" <<EOF
[Unit]
Description=SDRForge native radio server
After=pipewire.service wireplumber.service

[Service]
Type=simple
Environment=PYTHONUNBUFFERED=1
ExecStart="$python_bin" -m sdrforge.live_transport_server
Restart=on-failure
RestartSec=2

[Install]
WantedBy=default.target
EOF
sudo install -d -m 0755 /etc/openroadcode
printf '%s\n' "$(id -un)" | sudo tee /etc/openroadcode/sdrforge-user >/dev/null
systemctl --user daemon-reload
systemctl --user enable libsdrforge.service
systemctl --user restart libsdrforge.service
systemctl --user is-active libsdrforge.service
