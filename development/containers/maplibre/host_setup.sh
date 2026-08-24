#!/bin/bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

# MapLibre Native and the OpenRoadCode renderer are built in a container but
# execute on the host. Keep their host-side runtime/development dependency
# contract here so higher-level installers can simply invoke this helper.
sudo apt-get update
sudo apt-get install -y \
    libglfw3 \
    libshp4 \
    libglfw3-dev \
    libgles-dev \
    libuv1-dev \
    libjpeg62-turbo

echo "MapLibre host dependencies installed."
