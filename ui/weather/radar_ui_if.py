# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Immutable radar replay presentation, independent of providers and toolkits."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum


class RadarPalette(str, Enum):
    UNIVERSAL = "universal"
    CLASSIC = "classic"


@dataclass(frozen=True, slots=True)
class RadarUiState:
    enabled: bool = False
    frame_time: int | None = None
    times: tuple[int, ...] = ()
    index: int | None = None
    playing: bool = False
    forecast: bool = False
    loading: bool = False
    speed: float = 1.0
    palette: RadarPalette = RadarPalette.UNIVERSAL
    status: str = ""
    data_status: str = ""
    refreshed_at: float | None = None


class RadarUiIf(ABC):
    """Receive complete replay state without a radar controller reference."""

    @abstractmethod
    def set_radar_state(self, state: RadarUiState) -> None:
        """Present the current radar controls and loading/error state.

        @param state Immutable radar replay snapshot.
        """
        ...
