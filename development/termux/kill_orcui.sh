#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail
PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"

# Use the shared cleanup so renderer children and diagnostic UI launches are
# stopped too. Broker and supervised navigation services remain running.
exec bash "$PROJECT_ROOT/scripts/runtime/kill_orc.sh"
