#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
unset PYTHONPATH PYTHONHOME
export PYTHONNOUSERSITE=1
if [ ! -x .venv-quality/bin/python ]; then
    echo "Run bash scripts/setup_quality_env.sh first." >&2
    exit 1
fi
if [ -n "${TERMUX_VERSION:-}" ] || [[ "${PREFIX:-}" == */com.termux/files/usr ]]; then
    if [ "${ORC_QUALITY_CAPTURE:-0}" != 1 ]; then
        log="$(mktemp "${TMPDIR:-$PREFIX/tmp}/orc-quality.XXXXXX")"
        trap 'rm -f "$log"' EXIT
        status=0
        ORC_QUALITY_CAPTURE=1 bash "$0" "$@" 2>&1 | tee "$log" || status=$?
        if (( status != 0 )); then
            timeout 5 termux-clipboard-set < "$log" || true
        fi
        exit "$status"
    fi
fi
source .venv-quality/bin/activate
revision="$(git rev-parse --short HEAD 2>/dev/null || printf unknown)"
printf '[*] Revision: %s\n[*] Python: %s\n' "$revision" "$PWD/.venv-quality/bin/python"
mode="${1:---all}"
if [ "$#" -gt 0 ]; then shift; fi
case "$mode" in
    --lint) ruff check "${@:-.}"; ruff format --check "${@:-.}" ;;
    --format) python scripts/dev_check_changes.py --format-only "$@" ;;
    --types) python scripts/check_ui_types.py ;;
    --docstrings) python scripts/check_doxygen_contracts.py ;;
    --test) python scripts/run_tests.py unit "$@" ;;
    --all) python scripts/dev_check_changes.py --checks-only "$@" ;;
    --fix|--publish) python scripts/dev_check_changes.py --checks-only "$mode" "$@" ;;
    --docs)
        python scripts/docs_inventory.py --check
        python scripts/check_markdown_links.py
        python scripts/check_mermaid_legends.py
        python scripts/check_doxygen_contracts.py
        if [ -n "${TERMUX_VERSION:-}" ] || [[ "${PREFIX:-}" == */com.termux/files/usr ]]; then
            echo "Pinned Doxygen generation requires Linux x86-64 CI."
            exit 1
        fi
        bash scripts/install_quality_doxygen.sh
        mkdir -p build
        rm -f build/doxygen-warnings.log
        status=0
        doxygen Doxyfile || status=$?
        if [[ -s build/doxygen-warnings.log ]]; then
            cat build/doxygen-warnings.log >&2
            exit 1
        fi
        exit "$status"
        ;;
    --full) python scripts/dev_check_changes.py "$@" ;;
    *) echo "Usage: $0 [--all|--lint|--format|--types|--docstrings|--docs|--test|--full] [--fix] [--publish] [--message TEXT]" >&2; exit 2 ;;
esac
