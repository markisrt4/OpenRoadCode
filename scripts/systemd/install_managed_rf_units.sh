#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Sourced by install_sdrforge_user_systemd.sh after checking the primary ports.

readsb_bin="$(command -v readsb)" || {
  echo "[!] Install the ADS-B feature before enabling managed RF." >&2
  exit 1
}
command -v flock >/dev/null || {
  echo "[!] Install util-linux before enabling managed RF." >&2
  exit 1
}

mkdir -p "$(dirname -- "$rf_config")"
exec 8>"${rf_config}.lock"
if ! flock --nonblock 8; then
  echo "[!] Close OpenRoadCode before updating managed RF services." >&2
  exit 1
fi

# The vendor unit must never acquire hardware on its own after managed setup.
sudo systemctl disable --now readsb.service
sudo systemctl mask readsb.service
printf 'd /run/readsb 0755 %s %s -\n' "$(id -u)" "$(id -g)" |
  sudo tee /etc/tmpfiles.d/openroadcode-readsb.conf >/dev/null
sudo systemd-tmpfiles --create /etc/tmpfiles.d/openroadcode-readsb.conf

cat > "$unit_dir/openroadcode-readsb@.service" <<EOF
[Unit]
Description=OpenRoadCode readsb receiver %I
After=network.target

[Service]
Type=simple
ExecStart="$readsb_bin" --quiet --device-type=rtlsdr --device=%I --gain=auto --write-json=/run/readsb
NoNewPrivileges=yes
KillMode=control-group
Restart=no
EOF

cat > "$unit_dir/libsdrforge-weather.service" <<EOF
[Unit]
Description=SDRForge NOAA receiver transports
After=pipewire.service wireplumber.service

[Service]
Type=simple
EnvironmentFile="${rf_config//%/%%}"
ExecStart="$python_bin" -m sdrforge.live_transport_server --rest-port=5572 --rigctl-port=4533 --zmq-endpoint=tcp://127.0.0.1:5573 --presets-path=%t/openroadcode-weather-presets.json
Restart=no
EOF

if [[ -L "$rf_config" ]] || [[ -e "$rf_config" && ( ! -O "$rf_config" || "$(stat -c %a "$rf_config")" != 600 ) ]]; then
  echo "[!] Managed RF credential file must be owned by this user with mode 0600." >&2
  exit 1
fi
if [[ ! -f "$rf_config" ]]; then
  rf_credential_tmp="$(mktemp "${rf_config}.XXXXXX")"
  if "$python_bin" -c 'import secrets; print("SDRFORGE_ACQUISITION_TOKEN=" + secrets.token_hex(32))' > "$rf_credential_tmp"; then
    mv -n -- "$rf_credential_tmp" "$rf_config"
  fi
  rm -f -- "$rf_credential_tmp"
fi
mapfile -t rf_credentials < "$rf_config"
if (( ${#rf_credentials[@]} != 1 )) || [[ ! "${rf_credentials[0]:-}" =~ ^SDRFORGE_ACQUISITION_TOKEN=[a-f0-9]{64}$ ]]; then
  echo "[!] Managed RF credential file is invalid." >&2
  exit 1
fi

verify_managed_rf_units() {
  local unit=libsdrforge-weather.service pid attempt
  systemctl --user start "$unit"
  for (( attempt=0; attempt<10; attempt++ )); do
    pid="$(systemctl --user show "$unit" -p MainPID --value)"
    if owns_ports "$pid" 5572 5573 4533 &&
       "$python_bin" -c 'import json, urllib.request; status = json.load(urllib.request.urlopen("http://127.0.0.1:5572/v1/receiver", timeout=1)); assert not status["running"] and not status["starting"] and status["hardware_released"] is True' 2>/dev/null; then
      echo "[+] NOAA transport is ready and RF acquisition is idle."
      systemctl --user stop "$unit"
      return
    fi
    sleep 1
  done
  echo "[!] NOAA transport failed readiness or receiver release verification." >&2
  systemctl --user status "$unit" --no-pager >&2 || true
  return 1
}
