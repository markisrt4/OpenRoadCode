# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""UI-independent POI search and selection controller."""

from __future__ import annotations

from controllers.poi.poi_enricher import enrich_poi
from controllers.poi.poi_models import PoiCategory, PoiSearchResult, PointOfInterest
from controllers.poi.poi_search_controller_if import PoiSearchControllerIf
from protocols.map_renderer.map_poi_source import MapPoiSource, RawMapPoi


class PoiSearchController(PoiSearchControllerIf):
    """Translate renderer place data into semantic OpenRoadCode POIs."""

    def __init__(self, source: MapPoiSource | None = None) -> None:
        self._source = source or MapPoiSource()
        self._active_category: PoiCategory | None = None

    def search(self, category: PoiCategory) -> None:
        self._active_category = category
        self._source.request_search(category.name.casefold())

    def poll_selected(self) -> PointOfInterest | None:
        raw = self._source.poll_selected()
        if raw is None:
            return None
        return enrich_poi(self._to_poi(raw))

    def poll_search_result(self) -> PoiSearchResult | None:
        raw = self._source.poll_search_result()
        if raw is None:
            return None
        try:
            category = PoiCategory[raw.category.upper()]
        except KeyError:
            category = PoiCategory.OTHER
        return PoiSearchResult(
            category=category,
            count=raw.count,
            south=raw.south,
            west=raw.west,
            north=raw.north,
            east=raw.east,
        )

    def clear(self) -> None:
        self._active_category = None
        self._source.clear()

    def close(self) -> None:
        self._source.close()

    @staticmethod
    def _to_poi(raw: RawMapPoi) -> PointOfInterest:
        return PointOfInterest(
            poi_id=raw.poi_id,
            name=raw.name,
            category=_category_for(raw),
            position=raw.position,
            brand=raw.brand,
            source_class=raw.source_class,
            source_subclass=raw.source_subclass,
        )


def _category_for(raw: RawMapPoi) -> PoiCategory:
    source_class = (raw.source_class or "").casefold()
    source_subclass = (raw.source_subclass or "").casefold()
    if source_class in {"restaurant", "fast_food", "cafe", "food"} or source_subclass in {
        "restaurant", "fast_food", "cafe"
    }:
        return PoiCategory.FOOD
    if source_class in {"fuel", "gas_station"} or source_subclass in {"fuel", "gas_station"}:
        return PoiCategory.FUEL
    if source_class in {"grocery", "supermarket"} or source_subclass in {
        "grocery", "supermarket", "convenience"
    }:
        return PoiCategory.GROCERY
    return PoiCategory.OTHER
