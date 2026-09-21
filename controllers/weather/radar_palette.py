# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Radar presentation palettes independent of upstream providers."""

from enum import Enum


class RadarPalette(str, Enum):
    """Presentation applied to radar tiles."""

    UNIVERSAL = "universal"
    CLASSIC = "classic"
