#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$(cd -- "$SCRIPT_DIR/../.." && pwd)}"
VENV_DIR="${VENV_DIR:-$PROJECT_DIR/venv}"

fail() { echo "[!] $*" >&2; exit 1; }

[[ "$(uname -s)" == Linux && ! -e /system/bin/am ]] || fail "Waydroid requires native Linux."
(( EUID != 0 )) || fail "Run as the desktop user, not root."
case "$(uname -m)" in
  aarch64|x86_64) ;;
  *) fail "Waydroid requires a 64-bit ARM or x86 host." ;;
esac

systemctl --user show-environment >/dev/null || fail "A running user systemd session is required."
sudo -v
if ! grep -qw binder /proc/filesystems && ! grep -qw binderfs /proc/filesystems && [[ ! -c /dev/binder && ! -c /dev/anbox-binder ]]; then
  sudo modprobe binder_linux || fail "Binder unavailable; install a compatible kernel before continuing."
fi
if ! grep -qw binder /proc/filesystems && ! grep -qw binderfs /proc/filesystems && [[ ! -c /dev/binder && ! -c /dev/anbox-binder ]]; then
  fail "No Binder filesystem or device detected."
fi

missing_packages=()
for executable in waydroid weston adb scrcpy; do
  command -v "$executable" >/dev/null 2>&1 || missing_packages+=("$executable")
done
if (( ${#missing_packages[@]} )); then
  sudo apt update
  needs_backports=0
  for package in "${missing_packages[@]}"; do
    if ! apt-cache show "$package" >/dev/null 2>&1; then needs_backports=1; fi
  done
  if (( needs_backports )) && ( . /etc/os-release; [[ "${VERSION_CODENAME:-}" == trixie && "${ID:-}" == debian ]] ); then
    if ! sudo test -e /etc/apt/sources.list.d/openroadcode-backports.list; then
      printf '%s\n' 'deb [signed-by=/usr/share/keyrings/debian-archive-keyring.gpg] https://deb.debian.org/debian trixie-backports main contrib' |
        sudo tee /etc/apt/sources.list.d/openroadcode-backports.list >/dev/null
    fi
    sudo apt update
  fi
  for package in "${missing_packages[@]}"; do
    apt-cache show "$package" >/dev/null 2>&1 || fail "Required package unavailable: $package. Configure a compatible signed repository before continuing."
  done
  sudo apt install -y --no-install-recommends "${missing_packages[@]}"
fi
for executable in waydroid weston adb scrcpy; do
  command -v "$executable" >/dev/null 2>&1 || fail "Missing required executable: $executable"
done

if sudo test -s /var/lib/waydroid/waydroid.cfg; then
  echo "[*] Preserving existing Waydroid configuration and images."
elif sudo test -d /var/lib/waydroid && [[ -n "$(sudo find /var/lib/waydroid -mindepth 1 -maxdepth 1 -print -quit)" ]]; then
  fail "Existing Waydroid directory without a valid configuration; inspect it manually before initialization."
else
  sudo waydroid init
fi
sudo test -s /var/lib/waydroid/waydroid.cfg || fail "Waydroid initialization did not produce a configuration."
"$VENV_DIR/bin/python" "$PROJECT_DIR/scripts/install_waydroid_services.py" install

echo "[+] Waydroid services installed; ORC has not been launched."
echo "[*] From your X11 desktop, start Android with:"
echo "    bash development/debian/start_waydroid_services.sh"
echo "[*] Install Waze inside Android and complete its first-run prompts."
echo "[*] Enable a live GPS source in ORC; Android location sharing is prepared at service startup."
echo "[*] Pi 5 graphics, input and GPS delivery still require hardware verification."
