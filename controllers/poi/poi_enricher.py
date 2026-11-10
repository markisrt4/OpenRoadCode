# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Enrich raw map places with OpenRoadCode semantic actions."""

from __future__ import annotations

from dataclasses import replace

from tools.map_builder.builder.web_urls import valid_website
from ui.navigation.poi_models import (PoiAction, PoiActionKind, PointOfInterest, PoiIcon, PoiTitleStyle, PoiCategory)
from controllers.poi.business_catalog import resolve_business
from controllers.poi.business_provider_catalog import get_business_provider
from controllers.poi.business_icons import icon_bytes


def enrich_poi(poi: PointOfInterest) -> PointOfInterest:
    """Return a POI with actions derived from known place metadata."""
    actions: list[PoiAction] = []
    brand = poi.brand
    ordering = False

    website = valid_website(poi.website)
    business = resolve_business(brand=poi.brand, name=poi.name,
                                brand_wikidata=poi.brand_wikidata, operator=poi.operator,
                                website=website, category=None if poi.category is PoiCategory.OTHER else poi.category.name.casefold())
    if business is not None:
        brand = business.brand
        provider = get_business_provider(business.provider_id)
        if "order" in business.capabilities and provider is not None and provider.order_url:
            ordering = True
            actions.append(
                PoiAction(
                    PoiActionKind.ORDER,
                    "ORDER",
                    provider_id=business.provider_id,
                )
            )
        if not ordering and provider is not None and provider.android_package:
            actions.append(PoiAction(PoiActionKind.OPEN_ANDROID_APP, 'OPEN / INSTALL APP', provider_id=business.provider_id))

    if website and not ordering:
        actions.append(PoiAction(PoiActionKind.OPEN_WEBSITE, "WEBSITE", uri=website))
    image = icon_bytes(business.icon_id) if business else None
    return replace(poi, brand=brand, website=website, actions=tuple(actions),
                   business_id=business.provider_id if business else None,
                   icon_id=business.icon_id if business else None,
                   icon=PoiIcon(image) if image else None,
                   title_style=PoiTitleStyle(business.title_color, business.title_fonts)
                   if business is not None and business.title_color else None)
