#!/data/data/com.termux/files/usr/bin/bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
VENV_DIR="${VENV_DIR:-$PROJECT_ROOT/venv-termux}"

export DISPLAY="${DISPLAY:-:1}"
export PYTHONPATH="$PROJECT_ROOT${PYTHONPATH:+:$PYTHONPATH}"

if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  echo "[!] Termux virtual environment not found: $VENV_DIR" >&2
  echo "    Run scripts/termux/install.sh first." >&2
  exit 1
fi

cd "$PROJECT_ROOT"

if (( $# == 0 )); then
  set -- -m apps.carUi.main
fi

echo "[*] OpenRoadCode root: $PROJECT_ROOT"
echo "[*] DISPLAY:           $DISPLAY"
echo "[*] Python:            $VENV_DIR/bin/python"
echo "[*] Command:           python $*"

exec "$VENV_DIR/bin/python" "$@"
