# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Enrich raw map places with OpenRoadCode semantic actions."""

from __future__ import annotations

from dataclasses import replace

from tools.map_builder.builder.web_urls import valid_website

from controllers.poi.poi_models import PoiAction, PoiActionKind, PoiCategory, PointOfInterest
from controllers.poi.business_catalog import resolve_business


def enrich_poi(poi: PointOfInterest) -> PointOfInterest:
    """Return a POI with actions derived from known place metadata."""
    actions: list[PoiAction] = []
    brand = poi.brand

    if poi.category is PoiCategory.FOOD:
        business = resolve_business(brand=poi.brand, name=poi.name)
        if business is not None:
            brand = business.brand
            if "order" in business.capabilities:
                actions.append(
                    PoiAction(
                        PoiActionKind.ORDER,
                        "ORDER",
                        provider_id=business.provider_id,
                    )
                )

    website = valid_website(poi.website)
    if website:
        actions.append(PoiAction(PoiActionKind.OPEN_WEBSITE, "WEBSITE", uri=website))
    return replace(poi, brand=brand, website=website, actions=tuple(actions))
