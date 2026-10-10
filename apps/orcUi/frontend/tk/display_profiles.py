# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Resolution-based display profiles for the integrated ORCui shell.

Keep device identity separate from layout selection: Pi 4 and Pi 5 may
use the same profile when attached to the same display geometry.
"""
from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class DisplayProfile:
    name: str
    width: int
    height: int
    side_nav_width: int
    context_rail_width: int
    top_bar_height: int
    bottom_bar_height: int

    @property
    def geometry(self) -> str:
        return f"{self.width}x{self.height}"


def parse_geometry(value: str) -> tuple[int, int]:
    """Parse Tk geometry, accepting an optional window position suffix."""
    match = re.fullmatch(r"\s*(\d+)x(\d+)(?:[+-]\d+[+-]\d+)?\s*", value)
    if match is None:
        raise ValueError(f"Invalid ORCui geometry: {value!r}")
    width, height = (int(match.group(1)), int(match.group(2)))
    if width <= 0 or height <= 0:
        raise ValueError("Display dimensions must be positive")
    return width, height


def select_display_profile(width: int, height: int) -> DisplayProfile:
    """Choose compact, standard, or HD layout metrics from pixel geometry."""
    if width <= 0 or height <= 0:
        raise ValueError("Display dimensions must be positive")
    if width <= 800 or height <= 480:
        return DisplayProfile("compact", width, height, 88, 220, 40, 44)
    if width <= 1024 or height <= 600:
        return DisplayProfile("standard", width, height, 108, 280, 44, 46)
    return DisplayProfile("hd", width, height, 132, 340, 48, 50)


def profile_for_geometry(value: str) -> DisplayProfile:
    """Resolve a profile from a Tk geometry string."""
    return select_display_profile(*parse_geometry(value))
