# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Retain the immutable marker metadata while Navigation remounts its view."""
from dataclasses import dataclass
from ui.navigation.poi_models import PointOfInterest


@dataclass
class PoiSelectionCache:
    """UI-thread-owned cache, scoped to the same lifetime as the renderer markers."""
    pois: tuple[PointOfInterest, ...] = ()
