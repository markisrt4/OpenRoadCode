# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Magnetic-field navigation bus message."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MagneticFieldStateMessage:
    timestamp: str
    source: str
    magnetic_field_ut: dict[str, float]
