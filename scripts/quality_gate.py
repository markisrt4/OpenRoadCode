#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Run the portable OpenRoadCode Python quality gate."""

from __future__ import annotations

import argparse
import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _is_termux() -> bool:
    prefix = os.environ.get("PREFIX", "")
    return bool(os.environ.get("TERMUX_VERSION")) or prefix.startswith("/data/data/com.termux/")


def _run(label: str, command: list[str]) -> bool:
    print(f"\n[*] {label}", flush=True)
    result = subprocess.run(command, cwd=PROJECT_ROOT, check=False)
    if result.returncode == 0:
        print(f"[PASS] {label}", flush=True)
        return True
    print(f"[FAIL] {label}", flush=True)
    return False


def ruff_executable() -> str | None:
    """Use Ruff from the selected interpreter's environment, including native Termux Ruff."""
    venv_ruff = Path(sys.executable).with_name("ruff")
    return str(venv_ruff) if venv_ruff.is_file() else shutil.which("ruff")


def _run_ruff() -> bool:
    ruff = ruff_executable()
    if ruff is None:
        print("\n[FAIL] Ruff executable is not installed", file=sys.stderr, flush=True)
        return False
    lint_ok = _run("Ruff lint", [ruff, "check", "."])
    format_ok = _run("Ruff format", [ruff, "format", "--check", "."])
    return lint_ok and format_ok


def _run_ui_types() -> bool:
    if _is_termux() and importlib.util.find_spec("mypy") is None:
        print(
            "\n[SKIP] Strict UI contract types: mypy unavailable on Termux; required in Linux/CI",
            flush=True,
        )
        return True
    return _run("Strict UI contract types", [sys.executable, "scripts/check_ui_types.py"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--checks-only", action="store_true", help="Run static checks without the test suites"
    )
    args = parser.parse_args(argv)
    checks = [
        _run_ruff(),
        _run_ui_types(),
        _run(
            "orcUi module-size architecture check",
            [sys.executable, "scripts/check_python_module_size.py"],
        ),
        _run("Project-wide UI boundaries", [sys.executable, "scripts/check_ui_boundaries.py"]),
        _run("Documentation index", [sys.executable, "scripts/docs_inventory.py", "--check"]),
        _run("Markdown links", [sys.executable, "scripts/check_markdown_links.py"]),
        _run(
            "Doxygen interface contracts",
            [sys.executable, "scripts/check_doxygen_contracts.py"],
        ),
        _run(
            "Mermaid diagram legends",
            [sys.executable, "scripts/check_mermaid_legends.py"],
        ),
    ]
    if not args.checks_only:
        checks.append(
            _run("Unit + integration tests", [sys.executable, "scripts/run_tests.py", "all"])
        )
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
