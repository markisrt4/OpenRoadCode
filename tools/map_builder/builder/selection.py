# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Persistence for the map builder's last accepted region selection."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable


def load_region_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema") != 1:
        raise ValueError("unsupported saved-selection format")
    regions = payload.get("regions")
    if not isinstance(regions, list) or not all(isinstance(item, str) for item in regions):
        raise ValueError("saved selection must contain a list of region IDs")
    return set(regions)


def save_region_ids(path: Path, region_ids: Iterable[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"schema": 1, "regions": sorted(set(region_ids))}
    temporary = path.with_suffix(path.suffix + ".part")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
