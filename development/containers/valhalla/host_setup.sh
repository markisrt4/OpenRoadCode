#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

# Valhalla is compiled in a target-matched container but executed on the host.
# Development packages intentionally pull the matching runtime SONAMEs for the
# host distribution.
packages=(
    libgeotiff-dev
    libczmq-dev
)

missing_packages=()
for package in "${packages[@]}"; do
    if ! dpkg-query -W -f='${Status}' "$package" 2>/dev/null | grep -q '^install ok installed$'; then
        missing_packages+=("$package")
    fi
done

if ((${#missing_packages[@]})); then
    echo "[*] Installing missing Valhalla host dependencies: ${missing_packages[*]}"
    sudo apt-get update
    sudo apt-get install -y "${missing_packages[@]}"
else
    echo "[*] Valhalla host dependencies are already installed"
fi
