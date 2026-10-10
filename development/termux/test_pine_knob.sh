#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
set -euo pipefail
PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"
exec "${OPENROADCODE_PYTHON:-python}" -m apps.launchers.component_test.cesium_viewer_cli \
  --latitude 42.750 --longitude -83.380 --label "Pine Knob" --distance-m 1200 \
  --no-imagery --no-buildings --no-tiles "$@"
