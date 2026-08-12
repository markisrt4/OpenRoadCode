#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

target_user="${SUDO_USER:-${USER:-$(id -un)}}"
features=()
requested_groups=()
show_plan=0

for argument in "$@"; do
  if [[ "$argument" == "--show-plan" ]]; then
    show_plan=1
  else
    features+=("$argument")
  fi
done

append_group() {
  local group="$1"
  if [[ " ${requested_groups[*]} " != *" $group "* ]]; then
    requested_groups+=("$group")
  fi
}

for feature in "${features[@]}"; do
  case "$feature" in
    input)
      append_group input
      ;;
    gps|automotive)
      append_group dialout
      ;;
    rtl-sdr|adsb|sdrpp)
      append_group plugdev
      ;;
    raspberry-pi|imu|environmental)
      append_group gpio
      append_group i2c
      ;;
  esac
done

if (( ${#requested_groups[@]} == 0 )); then
  echo "[*] No additional user groups are required by the selected features."
  exit 0
fi

echo "[*] Feature-requested user groups: ${requested_groups[*]}"
if (( show_plan )); then
  echo "[*] Plan only; no user groups were changed."
  exit 0
fi

available_groups=()
for group in "${requested_groups[@]}"; do
  if getent group "$group" >/dev/null 2>&1; then
    available_groups+=("$group")
  else
    echo "[!] User group is unavailable on this host; skipping: $group"
  fi
done

if (( ${#available_groups[@]} == 0 )); then
  exit 0
fi

joined_groups="$(IFS=,; echo "${available_groups[*]}")"
echo "[*] Adding $target_user to feature-required groups: $joined_groups"
sudo usermod -aG "$joined_groups" "$target_user"
echo "[*] Group changes take effect after logging out and back in."
