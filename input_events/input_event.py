# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Toolkit-, controller-, and hardware-independent physical input values."""

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
    """Strongly typed identifier for one physical input device.

    @param device_type Category of the physical device.
    @param instance Zero-based device instance within that category.
    """

    device_type: InputDeviceType
    instance: int = 0


class InputEventType(Enum):
    """Generic physical input events without assigned UI meaning."""

    BUTTON_PRESSED = auto()
    BUTTON_RELEASED = auto()
    ROTATED = auto()
    POINTER_MOVED = auto()
    TOUCH_DOWN = auto()
    TOUCH_UP = auto()
    TOUCH_MOVE = auto()


@dataclass(frozen=True, slots=True)
class InputEvent:
    """Describe one normalized physical input event.

    @param device_id Identifier of the device that emitted the event.
    @param event_type Category of physical activity.
    @param value Optional event-specific payload.
    """

    device_id: InputDeviceId
    event_type: InputEventType
    value: Any = None
