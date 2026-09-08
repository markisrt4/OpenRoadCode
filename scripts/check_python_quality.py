#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Run OpenRoadCode Python lint and module-size quality checks."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import subprocess
import sys

DEFAULT_MAX_LINES = 500
DEFAULT_ROOT = Path("apps/orcUi")
EXCLUDED_PARTS = {"__pycache__", "unit_test"}
# main.py is the legacy oversized composition module currently being dismantled.
# This ceiling prevents regression while allowing the staged extraction to land.
LEGACY_LIMITS = {Path("apps/orcUi/main.py"): 700}


def python_files(root: Path):
    for path in root.rglob("*.py"):
        if not any(part in EXCLUDED_PARTS for part in path.parts):
            yield path


def line_count(path: Path) -> int:
    with path.open("r", encoding="utf-8") as source:
        return sum(1 for _ in source)


def find_ruff() -> str | None:
    """Return the Ruff executable used by the active environment, if available."""
    venv_ruff = Path(sys.executable).with_name("ruff")
    if venv_ruff.is_file():
        return str(venv_ruff)
    return shutil.which("ruff")


def check_ruff() -> bool:
    """Run the repository Ruff lint configuration."""
    ruff = find_ruff()
    if ruff is None:
        print(
            "Ruff is not installed. Install it with the platform package manager "
            "or Python development environment.",
            file=sys.stderr,
        )
        return False

    result = subprocess.run([ruff, "check", "."], check=False)
    return result.returncode == 0


def check_module_sizes(root: Path, max_lines: int) -> bool:
    """Check ORC UI modules against the architecture line-count limits."""
    oversized: list[tuple[Path, int, int]] = []
    for path in python_files(root):
        count = line_count(path)
        limit = LEGACY_LIMITS.get(path, max_lines)
        if count > limit:
            oversized.append((path, count, limit))

    if not oversized:
        return True

    print("Python modules exceed the ORC UI architecture limit:")
    for path, count, limit in sorted(oversized):
        print(f"  {path}: {count} lines (limit {limit})")
    print("Split responsibilities into smaller modules instead of extending these files.")
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-lines", type=int, default=DEFAULT_MAX_LINES)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args()

    ruff_ok = check_ruff()
    module_sizes_ok = check_module_sizes(args.root, args.max_lines)
    return 0 if ruff_ok and module_sizes_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
