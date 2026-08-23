#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Interactively configure ACRCloud credentials for OpenRoadCode."""

from __future__ import annotations

import argparse
import getpass
import os
from pathlib import Path
import tempfile


DEFAULT_SECRETS_FILE = Path.home() / ".config" / "openroadcode" / "secrets.env"
ACRCLOUD_KEYS = ("ACRCLOUD_HOST", "ACRCLOUD_ACCESS_KEY", "ACRCLOUD_ACCESS_SECRET")


def read_assignments(path: Path) -> dict[str, str]:
    """Read existing simple environment assignments without evaluating them."""
    values: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return values
    for raw_line in lines:
        line = raw_line.strip()
        if line.startswith("export "):
            line = line[7:].lstrip()
        name, separator, value = line.partition("=")
        if separator and name.strip() in ACRCLOUD_KEYS:
            values[name.strip()] = value.strip().strip("'\"")
    return values


def update_secrets(path: Path, replacements: dict[str, str]) -> None:
    """Atomically replace ACRCloud assignments and preserve unrelated content."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        lines = []
    remaining = dict(replacements)
    updated: list[str] = []
    for raw_line in lines:
        candidate = raw_line.strip()
        if candidate.startswith("export "):
            candidate = candidate[7:].lstrip()
        name, separator, _value = candidate.partition("=")
        key = name.strip()
        if separator and key in replacements:
            if key in remaining:
                updated.append(f"{key}={remaining.pop(key)}")
            continue
        updated.append(raw_line)
    if updated and updated[-1].strip():
        updated.append("")
    updated.extend(f"{key}={remaining[key]}" for key in ACRCLOUD_KEYS if key in remaining)

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


def prompt_value(label: str, existing: str | None, *, secret: bool = False) -> str:
    suffix = " [press Enter to keep existing]" if existing else ""
    prompt = f"{label}{suffix}: "
    value = getpass.getpass(prompt) if secret else input(prompt)
    value = value.strip()
    if not value and existing:
        return existing
    if not value:
        raise ValueError(f"{label} cannot be empty")
    if "\n" in value or "\r" in value:
        raise ValueError(f"{label} cannot contain a newline")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--secrets-file", type=Path, default=DEFAULT_SECRETS_FILE)
    args = parser.parse_args()
    path = args.secrets_file.expanduser()
    existing = read_assignments(path)
    print(f"Configuring ACRCloud credentials in {path}")
    try:
        values = {
            "ACRCLOUD_HOST": prompt_value("ACRCloud host", existing.get("ACRCLOUD_HOST")),
            "ACRCLOUD_ACCESS_KEY": prompt_value("ACRCloud access key", existing.get("ACRCLOUD_ACCESS_KEY"), secret=True),
            "ACRCLOUD_ACCESS_SECRET": prompt_value("ACRCloud access secret", existing.get("ACRCLOUD_ACCESS_SECRET"), secret=True),
        }
    except (EOFError, KeyboardInterrupt):
        print("\nConfiguration cancelled; no changes were written.")
        return 1
    except ValueError as error:
        print(f"Configuration not written: {error}")
        return 1
    update_secrets(path, values)
    print(f"ACRCloud credentials saved to {path} (mode 600). Restart OpenRoadCode to load them.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
