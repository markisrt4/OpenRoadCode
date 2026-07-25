"""Pushbutton state definitions."""

from enum import Enum, auto


class PushButtonState(Enum):
    """Physical state of a pushbutton."""

    RELEASED = auto()
    PRESSED = auto()
