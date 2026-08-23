#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Interactively configure the YouTube Data API key for OpenRoadCode."""

from __future__ import annotations

import argparse
import getpass
import os
from pathlib import Path
import tempfile


DEFAULT_SECRETS_FILE = Path.home() / ".config" / "openroadcode" / "secrets.env"
YOUTUBE_KEY = "YOUTUBE_API_KEY"


def read_api_key(path: Path) -> str | None:
    """Read the existing YouTube API key without evaluating the secrets file."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return None
    for raw_line in reversed(lines):
        line = raw_line.strip()
        if line.startswith("export "):
            line = line[7:].lstrip()
        name, separator, value = line.partition("=")
        if separator and name.strip() == YOUTUBE_KEY:
            return value.strip().strip("'\"")
    return None


def update_secrets(path: Path, api_key: str) -> None:
    """Atomically replace the YouTube key while preserving other secrets."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        lines = []
    updated: list[str] = []
    inserted = False
    for raw_line in lines:
        candidate = raw_line.strip()
        if candidate.startswith("export "):
            candidate = candidate[7:].lstrip()
        name, separator, _value = candidate.partition("=")
        if separator and name.strip() == YOUTUBE_KEY:
            if not inserted:
                updated.append(f"{YOUTUBE_KEY}={api_key}")
                inserted = True
            continue
        updated.append(raw_line)
    if not inserted:
        if updated and updated[-1].strip():
            updated.append("")
        updated.append(f"{YOUTUBE_KEY}={api_key}")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.parent.chmod(0o700)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            output.write("\n".join(updated).rstrip() + "\n")
            output.flush()
            os.fsync(output.fileno())
        temporary_path.chmod(0o600)
        temporary_path.replace(path)
        path.chmod(0o600)
    finally:
        temporary_path.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--secrets-file", type=Path, default=DEFAULT_SECRETS_FILE)
    args = parser.parse_args()
    path = args.secrets_file.expanduser()
    existing = read_api_key(path)
    suffix = " [press Enter to keep existing]" if existing else ""
    try:
        api_key = getpass.getpass(f"YouTube Data API key{suffix}: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nConfiguration cancelled; no changes were written.")
        return 1
    if not api_key:
        api_key = existing or ""
    if not api_key or "\n" in api_key or "\r" in api_key:
        print("Configuration not written: YouTube Data API key cannot be empty or contain a newline.")
        return 1
    update_secrets(path, api_key)
    print(f"YouTube API key saved to {path} (mode 600). Restart OpenRoadCode to load it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
