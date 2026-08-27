# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Dependency-free GPS report types shared by readers and tests."""

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class GpsData:
    """Represent one normalized GPS provider report."""

    latitude: float | None = None
    longitude: float | None = None
    altitude: float | None = None
    speed: float | None = None
    track: float | None = None
    mode: int | None = None
    satellites_visible: int | None = None
    satellites_used: int | None = None

    @property
    def has_fix(self) -> bool:
        """Return whether the provider reports a 2D or 3D positional fix."""
        return self.mode is not None and self.mode >= 2


GpsCallback = Callable[[GpsData], None]
