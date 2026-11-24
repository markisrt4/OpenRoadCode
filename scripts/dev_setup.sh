#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

if [ -n "${TERMUX_VERSION:-}" ] || [ "${PREFIX:-}" = /data/data/com.termux/files/usr ]; then
    echo "Termux: using native Python environment"
    if ! command -v python >/dev/null 2>&1; then
        pkg install -y python
    fi
else
    if [ ! -f .venv/bin/activate ]; then
        python3 -m venv .venv
    fi
    source .venv/bin/activate
fi

ruff_requirement="$(python -c 'import tomllib; print("ruff" + tomllib.load(open("pyproject.toml", "rb"))["tool"]["ruff"]["required-version"])')"
python -m pip install pytest python-dateutil
if ! command -v ruff >/dev/null 2>&1 || ! ruff check --show-settings controllers/calendar/icalendar_parser.py >/dev/null 2>&1; then
    if [ -n "${TERMUX_VERSION:-}" ] || [ "${PREFIX:-}" = /data/data/com.termux/files/usr ]; then
        echo "Install or update native Ruff with pkg install ruff; required: $ruff_requirement" >&2
        exit 1
    fi
    python -m pip install "$ruff_requirement"
fi
ruff --version
python -m pytest --version
echo "Development prerequisites ready. Run bash scripts/dev_check.sh."
