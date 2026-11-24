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
# Refuse unknown listeners rather than terminating unrelated processes.
listener_pids() {
  ss -H -lntp "sport = :$1" | grep -oE 'pid=[0-9]+' | cut -d= -f2 | sort -u || true
}
owns_ports() {
  local pid="$1" port
  [[ "$pid" =~ ^[1-9][0-9]*$ ]] || return 1
  for port in 5570 5571 4532; do
    [[ "$(listener_pids "$port")" == "$pid" ]] || return 1
  done
}
managed_pid="$(systemctl --user show libsdrforge.service -p MainPID --value 2>/dev/null || true)"
if [[ -n "$(ss -H -lnt '( sport = :5570 or sport = :5571 or sport = :4532 )')" ]] && ! owns_ports "$managed_pid"; then
  pid="$(listener_pids 5570)"
  if owns_ports "$pid" && [[ "$(stat -c %u "/proc/$pid")" == "$(id -u)" ]] &&
     tr '\0' ' ' < "/proc/$pid/cmdline" | grep -Eq 'sdrforge-server|sdrforge.live_transport_server|live_transport_server.py' &&
     ! grep -Eq '\.service(/|$)' "/proc/$pid/cgroup" &&
     [[ -t 0 ]]; then
    read -r -p "Stop unmanaged SDRForge (PID $pid) and transfer ownership to systemd? [y/N] " answer
    if [[ "$answer" =~ ^[Yy]([Ee][Ss])?$ ]]; then
      "$python_bin" -m sdrforge.live_transport_server --stop-running
    fi
  fi
  if [[ -n "$(ss -H -lnt '( sport = :5570 or sport = :5571 or sport = :4532 )')" ]]; then
    echo "[!] Radio ports already occupied; stop the existing owner before retrying." >&2
    ss -lntp '( sport = :5570 or sport = :5571 or sport = :4532 )' >&2
    exit 1
  fi
fi
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
for (( attempt=0; attempt<30; attempt++ )); do
  pid="$(systemctl --user show libsdrforge.service -p MainPID --value)"
  if systemctl --user is-active --quiet libsdrforge.service && owns_ports "$pid" &&
     "$python_bin" -c 'import json, urllib.request; assert json.load(urllib.request.urlopen("http://127.0.0.1:5570/v1/health", timeout=1))["status"] == "ok"' 2>/dev/null; then
    echo "[+] SDRForge ready; systemd PID $pid owns REST, ZMQ and rigctl."
    exit 0
  fi
  sleep 1
done
echo "[!] SDRForge failed readiness or listener ownership verification." >&2
systemctl --user status libsdrforge.service --no-pager >&2 || true
sudo journalctl _SYSTEMD_USER_UNIT=libsdrforge.service "_UID=$(id -u)" -n 30 --no-pager >&2 || true
exit 1
