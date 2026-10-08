# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Compatibility exports; shared contracts live in the independent UI package."""

from ui.navigation.poi_models import (
    PoiCategory,
    TransitMode,
    PoiActionKind,
    PoiAction,
    PointOfInterest,
    PoiSearchResult,
)

__all__ = ['PoiCategory', 'TransitMode', 'PoiActionKind', 'PoiAction', 'PointOfInterest', 'PoiSearchResult']
