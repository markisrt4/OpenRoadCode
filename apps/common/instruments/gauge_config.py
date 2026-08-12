# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GaugeConfig:
    """Configure the scale, labels, dimensions, and precision of a gauge."""
    title: str
    unit: str
    min_value: float
    max_value: float
    width: int = 180
    height: int = 140
    precision: int = 1
