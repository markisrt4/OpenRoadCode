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
source .venv-quality/bin/activate
mode="${1:---all}"
if [ "$#" -gt 0 ]; then shift; fi
case "$mode" in
    --lint) ruff check "${@:-.}"; ruff format --check "${@:-.}" ;;
    --format) ruff check --fix "${@:-.}"; ruff format "${@:-.}" ;;
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
    *) echo "Usage: $0 [--all|--lint|--format|--types|--docstrings|--docs|--test|--full]" >&2; exit 2 ;;
esac
