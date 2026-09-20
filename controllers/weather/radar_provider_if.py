# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Provider-independent weather-radar contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RadarFrame:
    """One timestamped radar raster frame."""

    timestamp: int
    tile_url: str


class RadarProviderIf(ABC):
    """Discover radar frames without exposing provider transport details."""

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Return the stable provider identifier."""

    @abstractmethod
    def get_frames(self) -> tuple[RadarFrame, ...]:
        """Return available radar frames ordered oldest to newest."""
