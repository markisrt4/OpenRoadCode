"""UI contract and values for lighting state."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ui.lighting.lighting_request_handler_if import LightingRequestHandlerIf


@dataclass(frozen=True, slots=True)
class LightingColor:
    """Represent an RGB color with channels in the range 0..255.

    @param red Red channel value.
    @param green Green channel value.
    @param blue Blue channel value.
    """

    red: int
    green: int
    blue: int

    def __post_init__(self) -> None:
        for name, value in (
            ("red", self.red),
            ("green", self.green),
            ("blue", self.blue),
        ):
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{name} must be an integer")
            if not 0 <= value <= 255:
                raise ValueError(f"{name} must be in range 0..255")


@dataclass(frozen=True, slots=True)
class LightingState:
    """Contain one complete lighting presentation snapshot.

    @param connected Whether a lighting controller is connected.
    @param power_enabled Whether lighting output is enabled.
    @param color Selected RGB color.
    @param brightness_percent Selected brightness from 0 through 100.
    @param pattern_index Selected controller pattern.
    @param music_mode Selected music-reactive mode.
    @param status_message Optional user-visible status.
    @param error_message Optional user-visible error.
    """

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
        """Set the displayed lighting snapshot, or clear unavailable state.

        @param state Complete state snapshot, or None when unavailable.
        """
        ...

    @abstractmethod
    def set_lighting_request_handler(
        self,
        handler: "LightingRequestHandlerIf | None",
    ) -> None:
        """Connect or clear the handler for user lighting requests.

        @param handler Request consumer, or None to disconnect it.
        """
        ...
