# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Layer TOML configuration without coupling callers to profile filenames."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib


class TomlOverlayError(ValueError):
    """Raised when a TOML configuration layer cannot be loaded."""


def load_toml_layers(*paths: str | Path | None) -> dict[str, Any]:
    """Load TOML layers in order, with later values overriding earlier values.

    Nested tables are merged recursively. Lists and scalar values are replaced
    as complete values so TOML arrays remain deterministic.
    """
    merged: dict[str, Any] = {}
    for value in paths:
        if value is None:
            continue
        path = Path(value).expanduser().resolve()
        try:
            with path.open("rb") as file:
                layer = tomllib.load(file)
        except FileNotFoundError as exc:
            raise TomlOverlayError(f"TOML configuration file not found: {path}") from exc
        except tomllib.TOMLDecodeError as exc:
            raise TomlOverlayError(f"Invalid TOML in {path}: {exc}") from exc
        merged = merge_toml_tables(merged, layer)
    return merged


def merge_toml_tables(
    base: dict[str, Any],
    override: dict[str, Any],
) -> dict[str, Any]:
    """Return a recursive TOML-table merge without mutating either input."""
    result = deepcopy(base)
    for key, value in override.items():
        existing = result.get(key)
        if isinstance(existing, dict) and isinstance(value, dict):
            result[key] = merge_toml_tables(existing, value)
        else:
            result[key] = deepcopy(value)
    return result
