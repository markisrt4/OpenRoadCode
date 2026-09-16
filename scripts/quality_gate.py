#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Run the portable OpenRoadCode Python quality gate."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _is_termux() -> bool:
    prefix = os.environ.get("PREFIX", "")
    return bool(os.environ.get("TERMUX_VERSION")) or prefix.startswith(
        "/data/data/com.termux/"
    )


def _run(label: str, command: list[str]) -> bool:
    print(f"\n[*] {label}", flush=True)
    result = subprocess.run(command, cwd=PROJECT_ROOT, check=False)
    if result.returncode == 0:
        print(f"[PASS] {label}", flush=True)
        return True
    print(f"[FAIL] {label}", flush=True)
    return False


def _run_ruff() -> bool:
    if importlib.util.find_spec("ruff") is None:
        if _is_termux():
            print("\n[SKIP] Ruff unavailable on Termux", flush=True)
            return True
        print("\n[FAIL] Ruff is not installed", file=sys.stderr, flush=True)
        return False
    return _run("Ruff", [sys.executable, "-m", "ruff", "check", "."])


def main() -> int:
    checks = (
        _run_ruff(),
        _run(
            "orcUi module-size architecture check",
            [sys.executable, "scripts/check_python_module_size.py"],
        ),
        _run(
            "Doxygen interface contracts",
            [sys.executable, "scripts/check_doxygen_contracts.py"],
        ),
        _run(
            "Mermaid diagram legends",
            [sys.executable, "scripts/check_mermaid_legends.py"],
        ),
        _run(
            "Unit tests",
            [sys.executable, "scripts/run_tests.py", "unit"],
        ),
        _run(
            "Integration tests",
            [sys.executable, "scripts/run_tests.py", "integration"],
        ),
    )
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
