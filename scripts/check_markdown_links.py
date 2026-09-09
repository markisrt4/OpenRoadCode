#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Validate repository-local Markdown link destinations."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_PARTS = {
    ".git",
    ".github",
    ".venv",
    "venv",
    "__pycache__",
    "build",
    "dist",
}

INLINE_LINK_PATTERN = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
REFERENCE_LINK_PATTERN = re.compile(r"(?m)^\s*\[[^\]]+\]:\s*(\S+)")


def _markdown_files() -> list[Path]:
    """Return Markdown files that belong to the source tree."""
    files: list[Path] = []
    for path in PROJECT_ROOT.rglob("*.md"):
        relative = path.relative_to(PROJECT_ROOT)
        if EXCLUDED_PARTS.intersection(relative.parts):
            continue
        files.append(path)
    return sorted(files)


def _strip_optional_title(destination: str) -> str:
    """Remove an optional Markdown link title from a destination."""
    destination = destination.strip()
    if destination.startswith("<") and ">" in destination:
        return destination[1 : destination.index(">")]

    match = re.match(r"^(\S+)(?:\s+[\"'].*[\"'])?$", destination)
    return match.group(1) if match else destination


def _local_target(destination: str, source_path: Path) -> Path | None:
    """Resolve a repository-local link target or return None when not local."""
    destination = _strip_optional_title(destination)
    if not destination or destination.startswith("#"):
        return None

    parsed = urlsplit(destination)
    if parsed.scheme or parsed.netloc:
        return None
    if destination.startswith(("mailto:", "tel:")):
        return None

    decoded_path = unquote(parsed.path)
    if not decoded_path:
        return None

    if decoded_path.startswith("/"):
        target = PROJECT_ROOT / decoded_path.lstrip("/")
    else:
        target = source_path.parent / decoded_path

    try:
        return target.resolve(strict=False)
    except OSError:
        return target.absolute()


def _destinations(markdown: str) -> list[str]:
    """Extract inline, image, and reference-style Markdown destinations."""
    destinations = [match.group(1) for match in INLINE_LINK_PATTERN.finditer(markdown)]
    destinations.extend(
        match.group(1) for match in REFERENCE_LINK_PATTERN.finditer(markdown)
    )
    return destinations


def main() -> int:
    """Fail when a repository-local Markdown link points to a missing path."""
    failures: list[str] = []
    checked_files = 0
    checked_links = 0

    for path in _markdown_files():
        checked_files += 1
        markdown = path.read_text(encoding="utf-8")
        for destination in _destinations(markdown):
            target = _local_target(destination, path)
            if target is None:
                continue

            checked_links += 1
            try:
                target.relative_to(PROJECT_ROOT)
            except ValueError:
                failures.append(
                    f"{path.relative_to(PROJECT_ROOT)}: link escapes repository: "
                    f"{destination}"
                )
                continue

            if not target.exists():
                failures.append(
                    f"{path.relative_to(PROJECT_ROOT)}: missing link target: "
                    f"{destination}"
                )

    if failures:
        print("\n".join(failures), file=sys.stderr)
        print(
            f"{len(failures)} broken repository-local Markdown link(s)",
            file=sys.stderr,
        )
        return 1

    print(
        f"Validated {checked_links} repository-local Markdown links "
        f"across {checked_files} files."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
