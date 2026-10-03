#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

echo "install_zeromq_systemd.sh is deprecated; installing openroadcode-message-broker.service instead." >&2
exec "$SCRIPT_DIR/install_message_broker_systemd.sh" "$@"
