# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Requests for the embedded Waze map, independent of ORC's map camera."""

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Protocol


class WazeGesture(str, Enum):
    ZOOM_IN = "zoom-in"
    ZOOM_OUT = "zoom-out"
    PAN_UP = "pan-up"
    PAN_DOWN = "pan-down"
    PAN_LEFT = "pan-left"
    PAN_RIGHT = "pan-right"


@dataclass(frozen=True, slots=True)
class WazeGestureState:
    available: bool = False
    busy: bool = False
    status: str = ""


class WazeGestureAdapterIf(Protocol):
    @property
    def available(self) -> bool:
        """Report whether this capability is available.

        @return Whether the capability is available.
        """
        ...

    def perform(self, gesture: WazeGesture, cancelled: Callable[[], bool]) -> None:
        """Apply one gesture only to the owned viewer, releasing input on cancellation.

        @param gesture Pan or zoom action to perform.
        @param cancelled Callback reporting cancellation of this request.
        """
        ...


class WazeGestureRequestHandlerIf(Protocol):
    @property
    def state(self) -> WazeGestureState:
        """Read the current immutable presentation state.

        @return Current immutable state.
        """
        ...

    def request_gesture(self, gesture: WazeGesture) -> None:
        """Request one gesture on the owned Waze surface.

        @param gesture Pan or zoom action to perform.
        """
        ...

    def set_visible(self, visible: bool) -> None:
        """Update the visibility of the Waze gesture controls.

        @param visible Whether the owned surface is visible.
        """
        ...
