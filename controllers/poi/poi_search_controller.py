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
from controllers.navigation.position_snapshot_cache import DEFAULT_POSITION_CACHE_DIRECTORY, PositionSnapshotCache
from controllers.poi.poi_enricher import enrich_poi
from controllers.poi.poi_models import PoiCategory, PoiSearchResult, PointOfInterest, TransitMode
from controllers.poi.poi_search_controller_if import PoiSearchControllerIf
from controllers.poi.poi_search_source_if import PoiSearchBounds, PoiSearchQuery, PoiSearchSourceIf
from controllers.poi.sqlite_poi_search_source import SqlitePoiSearchSource
from protocols.map_renderer.map_poi_source import MapPoiSource, RawMapPoi
from ui.navigation import GeoPoint

_EARTH_RADIUS_M = 6_378_137.0
_NEARBY_RADIUS_M = 20_000.0
_NEARBY_LIMIT = 50
_DEFAULT_SEARCH_DATABASE = Path(os.environ.get("OPENROADCODE_DATA_ROOT", "/srv/openroadcode")) / "maps" / "search" / "openroadcode-search.sqlite"


class PoiSearchController(PoiSearchControllerIf):
    """Discover POIs offline while keeping renderer selection independent."""

    def __init__(self, source: MapPoiSource | None = None, *, search_source: PoiSearchSourceIf | None = None, position_provider: Callable[[], GeoPoint | None] | None = None) -> None:
        self._source = source or MapPoiSource()
        self._search_source = search_source
        self._owns_search_source = search_source is None
        self._position_provider = position_provider or self._default_position
        self._active_category: PoiCategory | None = None
        self._pending_search_result: PoiSearchResult | None = None
        self._visible_pois: tuple[PointOfInterest, ...] = ()

    def search(self, category: PoiCategory, transit_mode: TransitMode = TransitMode.ALL) -> None:
        self._active_category = category
        self._pending_search_result = None
        position = self._position_provider()
        if position is None:
            self._pending_search_result = PoiSearchResult(category=category, count=0, south=0.0, west=0.0, north=0.0, east=0.0, pois=())
            return
        pois = self._offline_source().search(PoiSearchQuery(category=category, bounds=_nearby_bounds(position, _NEARBY_RADIUS_M), limit=_NEARBY_LIMIT, transit_mode=transit_mode))
        pois = tuple(
            poi
            for poi in pois
            if _distance_m(position, poi.position) <= _NEARBY_RADIUS_M
        )
        self._visible_pois = pois
        self._pending_search_result = _result_for(category, pois)

    def poll_selected(self) -> PointOfInterest | None:
        raw = self._source.poll_selected()
        if raw is not None:
            return enrich_poi(self._to_poi(raw))

        poll_click = getattr(self._source, "poll_click", None)
        if poll_click is None:
            return None
        click = poll_click()
        if click is None:
            return None

        print(
            "[poi-controller] resolving click "
            f"against {len(self._visible_pois)} visible POIs "
            f"radius_m={click.selection_radius_m:.1f} "
            f"marker_id={click.marker_id!r}"
        )
        if click.marker_id is not None:
            for poi in self._visible_pois:
                if poi.poi_id == click.marker_id:
                    print(f"[poi-controller] selected by marker id {poi.name!r}")
                    return enrich_poi(poi)
            print(f"[poi-controller] marker id not found: {click.marker_id!r}")

        nearest: PointOfInterest | None = None
        nearest_distance_m = click.selection_radius_m
        for poi in self._visible_pois:
            distance_m = _distance_m(click.position, poi.position)
            if distance_m <= nearest_distance_m:
                nearest = poi
                nearest_distance_m = distance_m
        if nearest is None:
            print("[poi-controller] click matched no visible POI")
            return None
        print(
            f"[poi-controller] selected {nearest.name!r} "
            f"distance_m={nearest_distance_m:.1f}"
        )
        return enrich_poi(nearest)

    def poll_search_result(self) -> PoiSearchResult | None:
        result, self._pending_search_result = self._pending_search_result, None
        return result

    def clear(self) -> None:
        self._active_category = None
        self._pending_search_result = None
        self._visible_pois = ()
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
        state = PositionSnapshotCache(PersistentCache(DEFAULT_POSITION_CACHE_DIRECTORY)).load()
        if state is None or not state.has_fix or state.latitude_deg is None or state.longitude_deg is None:
            return None
        return GeoPoint(latitude_rad=math.radians(state.latitude_deg), longitude_rad=math.radians(state.longitude_deg), altitude_m=state.altitude_m)

    @staticmethod
    def _to_poi(raw: RawMapPoi) -> PointOfInterest:
        return PointOfInterest(poi_id=raw.poi_id, name=raw.name, category=_category_for(raw), position=raw.position, brand=raw.brand, source_class=raw.source_class, source_subclass=raw.source_subclass)


def _nearby_bounds(position: GeoPoint, radius_m: float) -> PoiSearchBounds:
    latitude_deg = math.degrees(position.latitude_rad)
    longitude_deg = math.degrees(position.longitude_rad)
    latitude_delta = math.degrees(radius_m / _EARTH_RADIUS_M)
    cos_latitude = max(1.0e-6, abs(math.cos(position.latitude_rad)))
    longitude_delta = math.degrees(radius_m / (_EARTH_RADIUS_M * cos_latitude))
    return PoiSearchBounds(south=max(-90.0, latitude_deg - latitude_delta), west=max(-180.0, longitude_deg - longitude_delta), north=min(90.0, latitude_deg + latitude_delta), east=min(180.0, longitude_deg + longitude_delta))


def _result_for(category: PoiCategory, pois: tuple[PointOfInterest, ...]) -> PoiSearchResult:
    if not pois:
        return PoiSearchResult(category=category, count=0, south=0.0, west=0.0, north=0.0, east=0.0, pois=())
    latitudes = [math.degrees(poi.position.latitude_rad) for poi in pois]
    longitudes = [math.degrees(poi.position.longitude_rad) for poi in pois]
    return PoiSearchResult(category=category, count=len(pois), south=min(latitudes), west=min(longitudes), north=max(latitudes), east=max(longitudes), pois=pois)


def _category_for(raw: RawMapPoi) -> PoiCategory:
    source_class = (raw.source_class or "").casefold()
    source_subclass = (raw.source_subclass or "").casefold()
    if source_class in {"restaurant", "fast_food", "cafe", "food"} or source_subclass in {"restaurant", "fast_food", "cafe"}:
        return PoiCategory.FOOD
    if source_class in {"fuel", "gas_station"} or source_subclass in {"fuel", "gas_station"}:
        return PoiCategory.FUEL
    if source_class in {"grocery", "supermarket"} or source_subclass in {"grocery", "supermarket", "convenience"}:
        return PoiCategory.GROCERY
    if source_class in {"bus", "public_transport", "railway"}:
        return PoiCategory.TRANSIT
    return PoiCategory.OTHER


def _distance_m(first: GeoPoint, second: GeoPoint) -> float:
    dlat = second.latitude_rad - first.latitude_rad
    dlon = second.longitude_rad - first.longitude_rad
    haversine = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(first.latitude_rad)
        * math.cos(second.latitude_rad)
        * math.sin(dlon / 2.0) ** 2
    )
    return 2.0 * _EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(haversine)))
