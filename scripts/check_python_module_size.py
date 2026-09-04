#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Fail when Python modules grow beyond the repository architecture limit."""

from __future__ import annotations

import argparse
from pathlib import Path

DEFAULT_MAX_LINES = 500
EXCLUDED_PARTS = {".git", "build", "venv", ".venv", "__pycache__"}


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
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()

    oversized: list[tuple[Path, int]] = []
    for path in python_files(args.root):
        count = line_count(path)
        if count > args.max_lines:
            oversized.append((path, count))

    if not oversized:
        return 0

    print(f"Python modules must not exceed {args.max_lines} lines:")
    for path, count in sorted(oversized):
        print(f"  {path}: {count} lines")
    print("Split responsibilities into smaller modules instead of extending these files.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
