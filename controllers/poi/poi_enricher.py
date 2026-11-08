# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Enrich raw map places with OpenRoadCode semantic actions."""

from __future__ import annotations

from dataclasses import replace

from tools.map_builder.builder.web_urls import valid_website
from ui.navigation.poi_models import (PoiAction, PoiActionKind, PointOfInterest)
from controllers.poi.business_catalog import resolve_business
from controllers.poi.business_provider_catalog import get_business_provider


def enrich_poi(poi: PointOfInterest) -> PointOfInterest:
    """Return a POI with actions derived from known place metadata."""
    actions: list[PoiAction] = []
    brand = poi.brand

    website = valid_website(poi.website)
    business = resolve_business(brand=poi.brand, name=poi.name,
                                brand_wikidata=poi.brand_wikidata, operator=poi.operator,
                                website=website, category=poi.category.name.casefold())
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
        provider = get_business_provider(business.provider_id)
        if provider is not None and provider.android_package:
            actions.append(PoiAction(PoiActionKind.OPEN_ANDROID_APP, 'OPEN / INSTALL APP', provider_id=business.provider_id))

    if website:
        actions.append(PoiAction(PoiActionKind.OPEN_WEBSITE, "WEBSITE", uri=website))
    return replace(poi, brand=brand, website=website, actions=tuple(actions),
                   business_id=business.provider_id if business else None,
                   icon_id=business.icon_id if business else None)
