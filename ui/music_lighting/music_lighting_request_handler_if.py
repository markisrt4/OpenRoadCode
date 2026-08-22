# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from abc import ABC, abstractmethod

from controllers.music_lighting.music_lighting_types import MusicLightingPatternId


class MusicLightingRequestHandlerIf(ABC):
    @abstractmethod
    def request_enabled(self, enabled: bool) -> None: ...

    @abstractmethod
    def request_pattern(self, pattern: MusicLightingPatternId) -> None: ...

    @abstractmethod
    def request_intensity(self, intensity: float) -> None: ...

    @abstractmethod
    def request_brightness_limit(self, percent: int) -> None: ...
