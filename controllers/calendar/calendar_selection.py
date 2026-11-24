# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Persistent provider-independent calendar selection by stable collection ID."""

from __future__ import annotations

import json
from pathlib import Path


def load_disabled_calendar_ids(path: Path) -> frozenset[str]:
    if not path.exists():
        return frozenset()
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("disabled_calendar_ids"), list):
        raise ValueError("Calendar selection must contain disabled_calendar_ids list")
    values = data["disabled_calendar_ids"]
    if any(not isinstance(item, str) or not item for item in values):
        raise ValueError("Calendar IDs must be nonempty strings")
    return frozenset(values)


def save_disabled_calendar_ids(path: Path, disabled: set[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".new")
    temporary.write_text(
        json.dumps({"disabled_calendar_ids": sorted(disabled)}, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def save_calendar_catalog(path: Path, calendars: dict[str, str]) -> None:
    """Publish discovered calendar names, including empty and failed collections."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".new")
    temporary.write_text(json.dumps(calendars, indent=2), encoding="utf-8")
    temporary.replace(path)


def load_calendar_catalog(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or any(
        not isinstance(key, str) or not isinstance(value, str) for key, value in data.items()
    ):
        raise ValueError("Invalid calendar catalog")
    return data
