# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Decoded ambient-light state bus message types."""

from __future__ import annotations

from dataclasses import dataclass

from messaging.contracts.common.timestamp import Timestamp


@dataclass(frozen=True, slots=True)
class AmbientLightStateData:
    illuminance_lux: float


@dataclass(frozen=True, slots=True)
class AmbientLightStateMessage:
    version: int
    timestamp: Timestamp
    source: str
    data: AmbientLightStateData
