# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from enum import Enum, auto


class UiAction(Enum):
    NAVIGATE_UP = auto()
    NAVIGATE_DOWN = auto()
    NAVIGATE_LEFT = auto()
    NAVIGATE_RIGHT = auto()

    SELECT = auto()
    BACK = auto()
    HOME = auto()

    VOLUME_UP = auto()
    VOLUME_DOWN = auto()
    VOLUME_MUTE = auto()
