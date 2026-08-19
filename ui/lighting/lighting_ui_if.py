# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""UI contract and values for lighting state."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ui.lighting.lighting_request_handler_if import LightingRequestHandlerIf


@dataclass(frozen=True, slots=True)
class LightingColor:
    """Represent an RGB color with channels in the range 0..255."""

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

    @classmethod
    def from_hex(cls, value: str) -> "LightingColor":
        """Create a color from ``#RRGGBB`` or ``RRGGBB`` text."""
        if not isinstance(value, str):
            raise TypeError("hex color must be a string")
        normalized = value.strip().removeprefix("#")
        if len(normalized) != 6:
            raise ValueError("hex color must contain exactly 6 hexadecimal digits")
        try:
            packed = int(normalized, 16)
        except ValueError as exc:
            raise ValueError("hex color contains non-hexadecimal characters") from exc
        return cls(
            red=(packed >> 16) & 0xFF,
            green=(packed >> 8) & 0xFF,
            blue=packed & 0xFF,
        )

    def to_hex(self) -> str:
        """Return the canonical upper-case ``#RRGGBB`` representation."""
        return f"#{self.red:02X}{self.green:02X}{self.blue:02X}"


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
