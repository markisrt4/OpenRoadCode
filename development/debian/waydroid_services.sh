#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
set -euo pipefail
project_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
cd "$project_root"
if [[ -x venv/bin/python ]]; then
    exec venv/bin/python -m scripts.install_waydroid_services "$@"
fi
exec python3 -m scripts.install_waydroid_services "$@"
