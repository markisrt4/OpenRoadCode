#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

# Valhalla is compiled in a target-matched container but executed on the host.
# Development packages intentionally pull the matching runtime SONAMEs for the
# host distribution.
sudo apt-get update
sudo apt-get install -y \
    libgeotiff-dev \
    libczmq-dev

echo "Valhalla host dependencies installed."
