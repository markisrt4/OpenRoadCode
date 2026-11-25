#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1
mode="${1:---all}"
case "$mode" in
    --all|--lint|--format|--test) ;;
    *) echo "Usage: bash scripts/dev_check.sh [--all|--lint|--format|--test] [paths...]" >&2; exit 2 ;;
esac
if [ "$#" -gt 0 ]; then shift; fi
if [ -f .venv/bin/activate ]; then
    source .venv/bin/activate
fi
export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"
log_dir="${XDG_CACHE_HOME:-$HOME/.cache}/openroadcode"
mkdir -p "$log_dir" || exit 1
log="$log_dir/dev-check.log"
run_checks() {
    local rc=0
    echo "=== Python environment ==="
    command -v python
    python -c 'from pathlib import Path; import controllers.calendar.icalendar_parser as module; p = Path(module.__file__).resolve(); print(p); assert p.is_relative_to(Path.cwd()), "Not importing checkout"' || return 1
    if [ "$mode" = --all ] || [ "$mode" = --lint ]; then
        ruff check "${@:-.}" || rc=1
    fi
    if [ "$mode" = --all ] || [ "$mode" = --format ]; then
        ruff format --check "${@:-.}" || rc=1
    fi
    if [ "$mode" = --all ] || [ "$mode" = --test ]; then
        # Load stdlib calendar before pytest can collect similarly named packages.
        # pytest.main uses the same test runner as python -m pytest.
        local pytest_bootstrap='import calendar; import sys; import pytest; sys.exit(pytest.main(sys.argv[1:]))'
        if [ "$#" -gt 0 ]; then
            python -c "$pytest_bootstrap" --import-mode=importlib "$@" -q || rc=1
        else
            python -c "$pytest_bootstrap" --import-mode=importlib tests/unit/ controllers/calendar/unit_test/ -q || rc=1
        fi
    fi
    return "$rc"
}
run_checks "$@" 2>&1 | tee "$log"
rc=$?
if command -v termux-clipboard-set >/dev/null 2>&1; then
    termux-clipboard-set < "$log" || true
elif [ -n "${WAYLAND_DISPLAY:-}" ] && command -v wl-copy >/dev/null 2>&1; then
    wl-copy < "$log" || true
elif [ -n "${DISPLAY:-}" ] && command -v xclip >/dev/null 2>&1; then
    xclip -selection clipboard < "$log" || true
fi
echo "Log saved to $log"
exit "$rc"
