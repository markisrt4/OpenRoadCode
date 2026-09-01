# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Enrich raw map places with OpenRoadCode semantic actions."""

from __future__ import annotations

from dataclasses import replace

from controllers.poi.poi_models import PoiAction, PoiActionKind, PoiCategory, PointOfInterest
from controllers.poi.restaurant_catalog import resolve_restaurant_poi


def enrich_poi(poi: PointOfInterest) -> PointOfInterest:
    """Return a POI with actions derived from known place metadata."""
    actions = [PoiAction(PoiActionKind.NAVIGATE, "NAVIGATE")]
    brand = poi.brand

    if poi.category is PoiCategory.FOOD:
        restaurant = resolve_restaurant_poi(brand=poi.brand, name=poi.name)
        if restaurant is not None:
            brand = restaurant.brand
            actions.append(
                PoiAction(PoiActionKind.OPEN_URI, "ORDER", restaurant.order_url)
            )

    return replace(poi, brand=brand, actions=tuple(actions))
