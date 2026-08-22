# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Semantic operational state for music-analysis frontends."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class MusicAnalysisStatus(Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    ACTIVE = "active"
    ZEROIZING = "zeroizing"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class MusicAnalysisUiState:
    status: MusicAnalysisStatus = MusicAnalysisStatus.STOPPED
    calibrated: bool = False
    sensitivity: float = 1.0
    error: str | None = None

    def __post_init__(self) -> None:
        if not 0.25 <= self.sensitivity <= 2.0:
            raise ValueError("sensitivity must be in range 0.25..2.0")
        if self.status is not MusicAnalysisStatus.ERROR and self.error is not None:
            raise ValueError("error text is only valid when status is ERROR")
