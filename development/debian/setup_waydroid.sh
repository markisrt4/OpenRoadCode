#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
set -euo pipefail

usage() {
    echo "Usage: bash development/debian/setup_waydroid.sh [--init-gapps]"
    echo "Ubuntu 24.04 experiment: install Waydroid, Weston and diagnostics."
    echo "--init-gapps downloads a Google-services Android image if not initialized."
    echo "For the managed display/network/ADB/location workflow, use waydroid_vm.sh."
    echo "Preserves existing images; does not install Waze or ARM translation."
}
initialize=false
case "${1:-}" in
    --help|-h) usage; exit 0 ;;
    --init-gapps) initialize=true ;;
    '') ;;
    *) usage >&2; exit 2 ;;
esac
if (( $# > 1 )); then usage >&2; exit 2; fi
fail() { echo "Error: $*" >&2; exit 1; }
[[ $EUID -ne 0 ]] || fail "run as your desktop user with sudo access"
# shellcheck source=/dev/null
source /etc/os-release
[[ ${ID:-} == ubuntu && ${VERSION_CODENAME:-} == noble ]] ||
    fail "currently supports Ubuntu 24.04 (noble) only; other Linux targets need validation"
case "$(dpkg --print-architecture)" in
    amd64|arm64) ;;
    *) fail "requires amd64 or arm64" ;;
esac
if [[ ! -d /sys/module/binder_linux ]]; then
    modinfo binder_linux >/dev/null 2>&1 ||
        fail "kernel has no discoverable binder_linux support; resolve kernel support first"
    sudo modprobe binder_linux
fi
sudo apt-get update
sudo apt-get install -y curl ca-certificates weston mesa-utils xdotool x11-utils adb python3 iproute2 iptables iputils-ping

has_waydroid_candidate() {
    # Consume the complete output: grep -q can close the pipe early and make
    # apt-cache fail with SIGPIPE under pipefail. Pin the parsed field's locale.
    LC_ALL=C apt-cache policy waydroid | awk '
        $1 == "Candidate:" && NF >= 2 && $2 != "(none)" { found = 1 }
        END { exit !found }
    '
}
if ! has_waydroid_candidate; then
    repository_script=$(mktemp)
    trap 'rm -f -- "$repository_script"' EXIT
    curl -fsSL https://repo.waydro.id -o "$repository_script"
    echo "Adding the official Waydroid APT repository for noble."
    # The downloaded script takes a positional distribution. Bash -s is only
    # appropriate when Bash itself reads the script from stdin.
    sudo bash "$repository_script" noble
    sudo apt-get update
fi
has_waydroid_candidate ||
    fail "Waydroid repository has no package candidate; inspect apt errors above"
sudo apt-get install -y waydroid

if "$initialize"; then
    if sudo test -s /var/lib/waydroid/waydroid.cfg; then
        echo "Existing Android configuration preserved; not changing image type."
    else
        sudo waydroid init -s GAPPS
    fi
    sudo systemctl start waydroid-container
fi
echo "Setup complete. See docs/waydroid_vm.md for the repeatable VM workflow."
echo "Next: bash development/debian/waydroid_vm.sh run (normal desktop user)."
