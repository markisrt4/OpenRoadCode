# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""UI contract and values for lighting state."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

from common.color import RgbColor

if TYPE_CHECKING:
    from ui.lighting.lighting_request_handler_if import LightingRequestHandlerIf


# Semantic alias retained for the lighting UI API while color representation and
# conversion remain generic and reusable outside lighting.
LightingColor = RgbColor


@dataclass(frozen=True, slots=True)
class LightingState:
    """Contain one complete lighting presentation snapshot."""

    connected: bool = False
    power_enabled: bool = False
    color: LightingColor = LightingColor(255, 255, 255)
    brightness_percent: int = 100
    pattern_index: int = 0
    music_mode: int = 0
    status_message: str | None = None
    error_message: str | None = None


class LightingUiIf(ABC):
    """Display complete lighting state and emit semantic lighting requests."""

    @abstractmethod
    def set_lighting_state(self, state: LightingState | None) -> None:
        ...

    @abstractmethod
    def set_lighting_request_handler(
        self,
        handler: "LightingRequestHandlerIf | None",
    ) -> None:
        ...
