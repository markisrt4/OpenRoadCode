#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

# Valhalla is compiled in the build container but executed on the host. Keep
# the host-side shared-library contract here rather than duplicating it in
# higher-level installers.
sudo apt-get update
sudo apt-get install -y \
    libgeotiff5 \
    libczmq4

echo "Valhalla host runtime dependencies installed."
