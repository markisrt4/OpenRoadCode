#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Fail when ORC UI Python modules grow beyond the architecture limit."""

from __future__ import annotations

import argparse
from pathlib import Path

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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-lines", type=int, default=DEFAULT_MAX_LINES)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args()

    oversized: list[tuple[Path, int, int]] = []
    for path in python_files(args.root):
        count = line_count(path)
        limit = LEGACY_LIMITS.get(path, args.max_lines)
        if count > limit:
            oversized.append((path, count, limit))

    if not oversized:
        return 0

    print("Python modules exceed the ORC UI architecture limit:")
    for path, count, limit in sorted(oversized):
        print(f"  {path}: {count} lines (limit {limit})")
    print("Split responsibilities into smaller modules instead of extending these files.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
