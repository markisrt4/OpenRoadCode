# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Semantic requests emitted by music-analysis frontends."""
from __future__ import annotations

from abc import ABC, abstractmethod


class MusicAnalysisRequestHandlerIf(ABC):
    @abstractmethod
    def request_zeroize(self) -> None: ...

    @abstractmethod
    def request_sensitivity(self, value: float) -> None: ...
