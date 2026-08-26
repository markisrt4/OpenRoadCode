# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Decoded magnetic-field navigation bus message types."""

from __future__ import annotations

from dataclasses import dataclass

from messaging.contracts.common.timestamp import Timestamp


@dataclass(frozen=True, slots=True)
class MagneticFieldVector:
    x: float
    y: float
    z: float


@dataclass(frozen=True, slots=True)
class MagneticFieldStateMessage:
    version: int
    timestamp: Timestamp
    source: str
    magnetic_field_ut: MagneticFieldVector
