# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Semantic user requests emitted by music visualizer frontends."""
from __future__ import annotations

from abc import ABC, abstractmethod

from .music_visualizer_types import KickMode, MusicVisualizationMode


class MusicVisualizerRequestHandlerIf(ABC):
    @abstractmethod
    def request_zeroize(self) -> None: ...

    @abstractmethod
    def request_sensitivity(self, value: float) -> None: ...

    @abstractmethod
    def request_song_recognition(self) -> None: ...

    @abstractmethod
    def request_lighting_enabled(self, enabled: bool) -> None: ...

    @abstractmethod
    def request_kick_mode(self, mode: KickMode) -> None: ...

    @abstractmethod
    def request_visualization_mode(self, mode: MusicVisualizationMode) -> None: ...
