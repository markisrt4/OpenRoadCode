"""
Generic input-domain types.

These types describe physical input activity without assigning UI meaning.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any


class InputDeviceType(Enum):
    """Supported categories of physical input devices."""

    KEYBOARD = auto()
    ROTARY_ENCODER = auto()
    PUSHBUTTON = auto()
    TOUCHSCREEN = auto()
    MOUSE = auto()


@dataclass(frozen=True, slots=True)
class InputDeviceId:
    """Strongly typed identifier for one physical input device."""

    device_type: InputDeviceType
    instance: int = 0


class InputEventType(Enum):
    """Generic physical input events."""

    BUTTON_PRESSED = auto()
    BUTTON_RELEASED = auto()

    ROTATED = auto()

    POINTER_MOVED = auto()

    TOUCH_DOWN = auto()
    TOUCH_UP = auto()
    TOUCH_MOVE = auto()


@dataclass(frozen=True, slots=True)
class InputEvent:
    """One generic physical input event."""

    device_id: InputDeviceId

    event_type: InputEventType

    value: Any = None
