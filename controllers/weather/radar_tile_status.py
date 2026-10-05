# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Immutable diagnostics for tiles requested for one radar frame."""
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RadarTileStatus:
    pending: int = 0
    loaded: int = 0
    failed: int = 0
    has_echoes: bool | None = None
