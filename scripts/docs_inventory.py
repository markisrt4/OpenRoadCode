#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Discover canonical documentation for the repository and website."""

from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import quote

IGNORED_DIRECTORIES = {".git", ".github", ".venv", "venv", "__pycache__", "build", "dist"}
CURATED_GUIDES = ("apps/orcUi/ARCHITECTURE.md",)
BEGIN = "<!-- BEGIN GENERATED DOCS INDEX -->"
END = "<!-- END GENERATED DOCS INDEX -->"
HEADING = re.compile(r"^#\s+(.+?)\s*#*\s*$", re.MULTILINE)


def display_name(value: str) -> str:
    return value.replace("_", " ").replace("-", " ").title()


def discover(source_root: Path) -> list[dict[str, str]]:
    """Return the same canonical document set for every consumer."""
    root = source_root.resolve()
    paths = set(root.rglob("README.md"))
    docs = root / "docs"
    if docs.is_dir():
        paths.update(path for path in docs.rglob("*.md") if path.name != "README.md")
    paths.update(root / path for path in CURATED_GUIDES if (root / path).is_file())
    paths.update(root / name for name in ("CONTRIBUTING.md",) if (root / name).is_file())
    result = []
    for path in sorted(paths):
        relative = path.relative_to(root)
        if IGNORED_DIRECTORIES.intersection(relative.parts) or not path.is_file():
            continue
        if path.name == "README.md":
            kind = "readme"
        elif relative.as_posix() in CURATED_GUIDES:
            kind = "curated"
        elif relative == Path("CONTRIBUTING.md"):
            kind = "contributing"
        else:
            kind = "guide"
        fallback = path.parent.name if kind == "readme" else path.stem
        match = HEADING.search(path.read_text(encoding="utf-8"))
        title = match.group(1).strip() if match else display_name(fallback or "Project")
        result.append({"path": relative.as_posix(), "kind": kind, "title": title})
    return result


def _label(path: Path) -> str:
    """Use stable directory names for the inventory, not mutable prose titles."""
    if path.name == "README.md":
        return display_name(path.parent.name or "Project")
    return display_name(path.stem)


def render_catalog(records: list[dict[str, str]]) -> str:
    """Render a complete, repository-relative Markdown catalog."""
    groups: dict[str, list[dict[str, str]]] = {}
    for record in records:
        path = Path(record["path"])
        if path == Path("docs/README.md"):
            continue
        group = path.parts[0] if len(path.parts) > 1 else "project"
        groups.setdefault(group, []).append(record)
    lines = [BEGIN, "", "## Complete documentation catalog", "", "Generated from the canonical documentation files. Every component README and standalone guide is listed here. Run `python scripts/docs_inventory.py --write` after adding or moving documentation.", ""]
    for group in sorted(groups, key=str.lower):
        lines.extend((f"### {display_name(group)}", ""))
        for record in sorted(groups[group], key=lambda item: item["path"].lower()):
            path = Path(record["path"])
            label = _label(path)
            parent = path.parent.as_posix()
            if parent not in (".", group, "docs"):
                label = f"{label} (`{parent}`)"
            destination = quote(os.path.relpath(path.as_posix(), "docs"), safe="/.-_")
            lines.append(f"- [{label}]({destination})")
        lines.append("")
    lines.append(END)
    return "\n".join(lines)


def update_index(markdown: str, catalog: str) -> str:
    """Replace only the generated region, preserving authored content."""
    if markdown.count(BEGIN) != 1 or markdown.count(END) != 1:
        raise ValueError("docs/README.md must contain exactly one ordered generated-index marker pair")
    start = markdown.index(BEGIN)
    end = markdown.index(END)
    if start >= end:
        raise ValueError("Generated-index markers are out of order")
    return markdown[:start] + catalog + markdown[end + len(END):]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--manifest", type=Path, help="Write the shared JSON document inventory")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true", help="Update the generated README catalog")
    mode.add_argument("--check", action="store_true", help="Fail if the README catalog is stale")
    args = parser.parse_args(argv)
    root = args.source.resolve()
    records = discover(root)
    if args.manifest:
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(json.dumps(records, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.write or args.check:
        index = root / "docs/README.md"
        current = index.read_text(encoding="utf-8")
        expected = update_index(current, render_catalog(records))
        if args.check and current != expected:
            sys.stderr.writelines(difflib.unified_diff(current.splitlines(True), expected.splitlines(True), fromfile="docs/README.md", tofile="generated index"))
            print("Documentation index is stale. Run python scripts/docs_inventory.py --write", file=sys.stderr)
            return 1
        if args.write and current != expected:
            index.write_text(expected, encoding="utf-8")
    print(f"Discovered {len(records)} canonical documentation files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
