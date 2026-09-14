#!/usr/bin/env python3
"""Require the ORC diagram legend in Markdown documents that use Mermaid."""

from __future__ import annotations

from pathlib import Path
import sys

EXCLUDED_PARTS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "build",
    "dist",
}

MERMAID_FENCE = "```mermaid"
LEGEND_MARKER = 'class="orc-diagram-legend"'


def iter_markdown(root: Path):
    for path in root.rglob("*.md"):
        if any(part in EXCLUDED_PARTS for part in path.parts):
            continue
        yield path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    missing = []

    for path in iter_markdown(root):
        text = path.read_text(encoding="utf-8")
        if MERMAID_FENCE in text and LEGEND_MARKER not in text:
            missing.append(path.relative_to(root))

    if missing:
        print("Mermaid documents missing the ORC diagram legend:", file=sys.stderr)
        for path in missing:
            print(f"  {path}", file=sys.stderr)
        return 1

    print("Mermaid legend check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
