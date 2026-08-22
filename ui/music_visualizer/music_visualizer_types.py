# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class KickMode(Enum):
    SINGLE = "single"
    DOUBLE = "double"


@dataclass(frozen=True, slots=True)
class SongRecognitionUiState:
    configured: bool
    recognizing: bool = False
    provider: str | None = None
