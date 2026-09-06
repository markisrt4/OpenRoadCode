# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Processed ambient light controller state."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class AmbientLightState:
    """Current ambient illuminance state."""

    timestamp: datetime
    illuminance_lux: float
