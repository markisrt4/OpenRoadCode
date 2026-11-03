# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Remembered navigation view, independent of either map's runtime."""
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class NavigationViewState:
    selected: Literal['map', 'waze'] = 'map'
