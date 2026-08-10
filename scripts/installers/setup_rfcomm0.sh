#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

echo "[!] setup_rfcomm0.sh is deprecated; use setup_bluetooth_spp.sh." >&2
exec "$SCRIPT_DIR/setup_bluetooth_spp.sh" "$@"
