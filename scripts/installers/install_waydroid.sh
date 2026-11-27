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
if ! grep -qw binder /proc/filesystems && ! grep -qw binderfs /proc/filesystems; then
  sudo modprobe binder_linux || fail "Binder unavailable; install a compatible kernel before continuing."
fi
if ! grep -qw binder /proc/filesystems && ! grep -qw binderfs /proc/filesystems && [[ ! -c /dev/binder && ! -c /dev/anbox-binder ]]; then
  fail "No Binder filesystem or device detected."
fi

if ! command -v waydroid >/dev/null 2>&1; then
  sudo apt update
  apt-cache show waydroid >/dev/null 2>&1 || fail "Waydroid package unavailable. Configure the official repository for your distribution: https://docs.waydro.id/usage/install-on-desktops"
  sudo apt install -y waydroid
fi
for executable in waydroid weston adb scrcpy; do
  command -v "$executable" >/dev/null 2>&1 || fail "Missing required executable: $executable"
done

if sudo test -s /var/lib/waydroid/waydroid.cfg; then
  echo "[*] Preserving existing Waydroid configuration and images."
elif sudo test -e /var/lib/waydroid; then
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
