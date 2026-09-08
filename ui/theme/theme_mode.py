# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Supported application theme modes."""

from enum import Enum


class ThemeMode(str, Enum):
    """Named visual modes understood by the theme controller."""

    DARK = "dark"
    LIGHT = "light"
