# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""UI-independent POI search and selection controller."""

from __future__ import annotations

import math
import os
from collections.abc import Callable
from pathlib import Path

from controllers.cache import PersistentCache
from controllers.navigation.current_position import get_current_position
from controllers.navigation.position_snapshot_cache import (
    DEFAULT_POSITION_CACHE_DIRECTORY,
    PositionSnapshotCache,
)
from controllers.poi.poi_enricher import enrich_poi
from controllers.poi.poi_models import PoiCategory, PoiSearchResult, PointOfInterest
from controllers.poi.poi_search_controller_if import PoiSearchControllerIf
from controllers.poi.poi_search_source_if import (
    PoiSearchBounds,
    PoiSearchQuery,
    PoiSearchSourceIf,
)
from controllers.poi.sqlite_poi_search_source import SqlitePoiSearchSource
from protocols.map_renderer.map_poi_source import MapPoiSource, RawMapPoi
from ui.navigation import GeoPoint

_EARTH_RADIUS_M = 6_378_137.0
_NEARBY_RADIUS_M = 20_000.0
_NEARBY_LIMIT = 50
_DEFAULT_SEARCH_DATABASE = (
    Path(os.environ.get("OPENROADCODE_DATA_ROOT", "/srv/openroadcode"))
    / "maps"
    / "search"
    / "openroadcode-search.sqlite"
)


class PoiSearchController(PoiSearchControllerIf):
    """Discover POIs offline while keeping renderer selection independent."""

    def __init__(
        self,
        source: MapPoiSource | None = None,
        *,
        search_source: PoiSearchSourceIf | None = None,
        position_provider: Callable[[], GeoPoint | None] | None = None,
    ) -> None:
        # Renderer events remain useful for selecting a POI that the user taps,
        # but discovery belongs to the renderer-independent offline search DB.
        self._source = source or MapPoiSource()
        self._search_source = search_source
        self._owns_search_source = search_source is None
        self._position_provider = position_provider or self._default_position
        self._active_category: PoiCategory | None = None
        self._pending_search_result: PoiSearchResult | None = None

    def search(self, category: PoiCategory) -> None:
        self._active_category = category
        self._pending_search_result = None

        position = self._position_provider()
        if position is None:
            self._pending_search_result = PoiSearchResult(
                category=category,
                count=0,
                south=0.0,
                west=0.0,
                north=0.0,
                east=0.0,
            )
            return

        bounds = _nearby_bounds(position, _NEARBY_RADIUS_M)
        pois = self._offline_source().search(
            PoiSearchQuery(
                category=category,
                bounds=bounds,
                limit=_NEARBY_LIMIT,
            )
        )
        self._pending_search_result = _result_for(category, pois)

    def poll_selected(self) -> PointOfInterest | None:
        raw = self._source.poll_selected()
        if raw is None:
            return None
        return enrich_poi(self._to_poi(raw))

    def poll_search_result(self) -> PoiSearchResult | None:
        result, self._pending_search_result = self._pending_search_result, None
        return result

    def clear(self) -> None:
        self._active_category = None
        self._pending_search_result = None
        self._source.clear()

    def close(self) -> None:
        self._source.close()
        if self._search_source is not None and self._owns_search_source:
            self._search_source.close()
            self._search_source = None

    def _offline_source(self) -> PoiSearchSourceIf:
        if self._search_source is None:
            self._search_source = SqlitePoiSearchSource(_DEFAULT_SEARCH_DATABASE)
        return self._search_source

    @staticmethod
    def _default_position() -> GeoPoint | None:
        live = get_current_position()
        if live is not None:
            return live
        cache = PositionSnapshotCache(PersistentCache(DEFAULT_POSITION_CACHE_DIRECTORY))
        state = cache.load()
        if (
            state is None
            or not state.has_fix
            or state.latitude_deg is None
            or state.longitude_deg is None
        ):
            return None
        return GeoPoint(
            latitude_rad=math.radians(state.latitude_deg),
            longitude_rad=math.radians(state.longitude_deg),
            altitude_m=state.altitude_m,
        )

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


def _nearby_bounds(position: GeoPoint, radius_m: float) -> PoiSearchBounds:
    latitude_deg = math.degrees(position.latitude_rad)
    longitude_deg = math.degrees(position.longitude_rad)
    latitude_delta = math.degrees(radius_m / _EARTH_RADIUS_M)
    cos_latitude = max(1.0e-6, abs(math.cos(position.latitude_rad)))
    longitude_delta = math.degrees(radius_m / (_EARTH_RADIUS_M * cos_latitude))
    return PoiSearchBounds(
        south=max(-90.0, latitude_deg - latitude_delta),
        west=max(-180.0, longitude_deg - longitude_delta),
        north=min(90.0, latitude_deg + latitude_delta),
        east=min(180.0, longitude_deg + longitude_delta),
    )


def _result_for(
    category: PoiCategory,
    pois: tuple[PointOfInterest, ...],
) -> PoiSearchResult:
    if not pois:
        return PoiSearchResult(
            category=category,
            count=0,
            south=0.0,
            west=0.0,
            north=0.0,
            east=0.0,
        )

    latitudes = [math.degrees(poi.position.latitude_rad) for poi in pois]
    longitudes = [math.degrees(poi.position.longitude_rad) for poi in pois]
    return PoiSearchResult(
        category=category,
        count=len(pois),
        south=min(latitudes),
        west=min(longitudes),
        north=max(latitudes),
        east=max(longitudes),
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
