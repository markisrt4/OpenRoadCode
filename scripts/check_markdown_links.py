#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Validate repository-local Markdown link destinations and section anchors."""

from __future__ import annotations

import html
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
HEADING_PATTERN = re.compile(r"(?m)^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$")
HTML_ID_PATTERN = re.compile(
    r"\b(?:id|name)\s*=\s*[\"']([^\"']+)[\"']",
    re.IGNORECASE,
)
HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
MARKDOWN_LINK_TEXT_PATTERN = re.compile(r"!?\[([^\]]*)\]\([^)]*\)")
MARKDOWN_PUNCTUATION_PATTERN = re.compile(r"[`*_~]")
SLUG_PUNCTUATION_PATTERN = re.compile(r"[^\w\-\s]", re.UNICODE)
WHITESPACE_PATTERN = re.compile(r"\s+")


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


def _local_destination(
    destination: str,
    source_path: Path,
) -> tuple[Path, str] | None:
    """Resolve a repository-local path and decoded fragment, if applicable."""
    destination = _strip_optional_title(destination)
    if not destination:
        return None

    parsed = urlsplit(destination)
    if parsed.scheme or parsed.netloc:
        return None
    if destination.startswith(("mailto:", "tel:")):
        return None

    decoded_path = unquote(parsed.path)
    fragment = unquote(parsed.fragment)

    if not decoded_path:
        if fragment:
            return source_path.resolve(strict=False), fragment
        return None

    if decoded_path.startswith("/"):
        target = PROJECT_ROOT / decoded_path.lstrip("/")
    else:
        target = source_path.parent / decoded_path

    try:
        resolved = target.resolve(strict=False)
    except OSError:
        resolved = target.absolute()
    return resolved, fragment


def _destinations(markdown: str) -> list[str]:
    """Extract inline, image, and reference-style Markdown destinations."""
    destinations = [match.group(1) for match in INLINE_LINK_PATTERN.finditer(markdown)]
    destinations.extend(
        match.group(1) for match in REFERENCE_LINK_PATTERN.finditer(markdown)
    )
    return destinations


def _heading_slug(heading: str) -> str:
    """Return a GitHub-style anchor slug for one Markdown heading."""
    value = HTML_TAG_PATTERN.sub("", heading)
    value = MARKDOWN_LINK_TEXT_PATTERN.sub(r"\1", value)
    value = MARKDOWN_PUNCTUATION_PATTERN.sub("", value)
    value = html.unescape(value).strip().lower()
    value = SLUG_PUNCTUATION_PATTERN.sub("", value)
    return WHITESPACE_PATTERN.sub("-", value)


def _markdown_anchors(path: Path) -> set[str]:
    """Return generated heading anchors and explicit HTML ids for a Markdown file."""
    markdown = path.read_text(encoding="utf-8")
    anchors = set(HTML_ID_PATTERN.findall(markdown))
    slug_counts: dict[str, int] = {}

    for match in HEADING_PATTERN.finditer(markdown):
        base_slug = _heading_slug(match.group(1))
        if not base_slug:
            continue
        count = slug_counts.get(base_slug, 0)
        slug_counts[base_slug] = count + 1
        slug = base_slug if count == 0 else f"{base_slug}-{count}"
        anchors.add(slug)

    return anchors


def main() -> int:
    """Fail when a repository-local Markdown link or anchor is invalid."""
    failures: list[str] = []
    checked_files = 0
    checked_links = 0
    checked_anchors = 0
    anchor_cache: dict[Path, set[str]] = {}

    for path in _markdown_files():
        checked_files += 1
        markdown = path.read_text(encoding="utf-8")
        for destination in _destinations(markdown):
            local = _local_destination(destination, path)
            if local is None:
                continue

            target, fragment = local
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
                continue

            if not fragment or target.suffix.lower() != ".md":
                continue

            checked_anchors += 1
            anchors = anchor_cache.setdefault(target, _markdown_anchors(target))
            if fragment not in anchors:
                failures.append(
                    f"{path.relative_to(PROJECT_ROOT)}: missing Markdown anchor "
                    f"#{fragment} in {target.relative_to(PROJECT_ROOT)}"
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
        f"({checked_anchors} section anchors) across {checked_files} files."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
