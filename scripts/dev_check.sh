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
        status=0
        ORC_QUALITY_CAPTURE=1 bash "$0" "$@" 2>&1 | tee "$log" || status=$?
        if (( status != 0 )); then
            echo "Diagnostic log retained: $log"
            timeout 5 termux-clipboard-set < "$log" || true
        else
            rm -f "$log"
        fi
        exit "$status"
    fi
fi
source .venv-quality/bin/activate
mode="${1:---all}"
if [ "$#" -gt 0 ]; then shift; fi
case "$mode" in
    --lint) ruff check "${@:-.}"; ruff format --check "${@:-.}" ;;
    --format) ruff check --fix "${@:-.}"; ruff format "${@:-.}" ;;
    --format-push)
        if [[ "$#" != 0 ]]; then
            echo "--format-push does not accept paths." >&2
            exit 2
        fi
        branch="$(git symbolic-ref --quiet --short HEAD)"
        if [[ -n "$(git status --porcelain --untracked-files=no)" ]]; then
            echo "Commit or restore tracked changes before automatic formatting." >&2
            exit 1
        fi
        git fetch origin
        git pull --ff-only origin "$branch"
        mapfile -d '' -t python_files < <(git ls-files -z -- '*.py')
        if (( ${#python_files[@]} > 0 )); then
            ruff check --force-exclude --fix --no-unsafe-fixes -- "${python_files[@]}"
            ruff format --force-exclude -- "${python_files[@]}"
            ruff check --force-exclude -- "${python_files[@]}"
            ruff format --force-exclude --check -- "${python_files[@]}"
        fi
        git diff --check
        git --no-pager diff
        if ! git diff --quiet; then
            git add -u -- '*.py'
            git commit -m "Apply safe Ruff corrections and formatting"
        fi
        git push origin "HEAD:refs/heads/$branch"
        python scripts/check_ui_types.py
        ;;
    --types) python scripts/check_ui_types.py ;;
    --docstrings) python scripts/check_doxygen_contracts.py ;;
    --test) python scripts/run_tests.py unit ;;
    --all)
        ruff check .
        ruff format --check .
        python scripts/check_ui_types.py
        python scripts/check_python_module_size.py
        python scripts/check_ui_boundaries.py
        python scripts/check_weather_ui_contracts.py
        python scripts/check_doxygen_contracts.py
        python scripts/check_mermaid_legends.py
        ;;
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
    --full) python scripts/quality_gate.py ;;
    *) echo "Usage: $0 [--all|--lint|--format|--format-push|--types|--docstrings|--docs|--test|--full]" >&2; exit 2 ;;
esac
