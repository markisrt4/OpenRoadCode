# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Compatibility exports; shared contracts live in the independent UI package."""

from ui.navigation.poi_models import (
    PoiAction,
    PoiActionKind,
    PoiCategory,
    PointOfInterest,
    PoiSearchResult,
    TransitMode,
)

__all__ = [
    "PoiCategory",
    "TransitMode",
    "PoiActionKind",
    "PoiAction",
    "PointOfInterest",
    "PoiSearchResult",
]
