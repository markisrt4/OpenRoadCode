#!/bin/bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

# MapLibre Native and the OpenRoadCode renderer are built in a target-matched
# container but execute on the host. Development packages intentionally pull
# the matching runtime SONAMEs for the host distribution.
sudo apt-get update
sudo apt-get install -y \
    libglfw3-dev \
    libshp-dev \
    libgles-dev \
    libuv1-dev \
    libjpeg-dev \
    libicu-dev

echo "MapLibre host dependencies installed."
