#!/bin/bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

# MapLibre Native and the OpenRoadCode renderer are built in a target-matched
# container but execute on the host. Development packages intentionally pull
# the matching runtime SONAMEs for the host distribution.
packages=(
    libglfw3-dev
    libshp-dev
    libgles-dev
    libuv1-dev
    libjpeg-dev
    libicu-dev
)

missing_packages=()
for package in "${packages[@]}"; do
    if ! dpkg-query -W -f='${Status}' "$package" 2>/dev/null | grep -q '^install ok installed$'; then
        missing_packages+=("$package")
    fi
done

if ((${#missing_packages[@]})); then
    echo "[*] Installing missing MapLibre host dependencies: ${missing_packages[*]}"
    sudo apt-get update
    sudo apt-get install -y "${missing_packages[@]}"
else
    echo "[*] MapLibre host dependencies are already installed"
fi
