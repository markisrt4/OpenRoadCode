# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""UI-independent POI search and selection controller."""

from __future__ import annotations

import logging

from common.logging.structured import current_operation
from common.logging.diagnostics import ComponentLog, diagnostic_action
import math
import sqlite3
from collections.abc import Callable

from common.navigation_data import search_database_path
from controllers.cache import PersistentCache
from controllers.navigation.current_position import get_current_position
from controllers.navigation.position_snapshot_cache import DEFAULT_POSITION_CACHE_DIRECTORY, PositionSnapshotCache
from controllers.poi.poi_enricher import enrich_poi
from ui.navigation.poi_models import (PoiCategory, PoiSearchResult, PointOfInterest, TransitMode)
from controllers.poi.poi_search_controller_if import PoiSearchControllerIf
from controllers.poi.poi_search_source_if import PoiSearchBounds, PoiSearchQuery, PoiSearchSourceIf
from controllers.poi.sqlite_poi_search_source import SqlitePoiSearchSource
from protocols.map_renderer.map_poi_source import MapPoiSource, RawMapPoi
from ui.navigation import GeoPoint


_EARTH_RADIUS_M = 6_378_137.0
_NEARBY_RADIUS_M = 20_000.0
_NEARBY_LIMIT = 50
def _default_search_database():
    return search_database_path()


class PoiSearchController(PoiSearchControllerIf):
    """Discover POIs offline while keeping renderer selection independent."""

    def __init__(self, source: MapPoiSource | None = None, *, search_source: PoiSearchSourceIf | None = None, position_provider: Callable[[], GeoPoint | None] | None = None) -> None:
        self._diagnostics = ComponentLog("navigation.poi", "poi")
        self._search_operation_id = None
        self._source = source or MapPoiSource()
        self._search_source = search_source
        self._owns_search_source = search_source is None
        self._position_provider = position_provider or self._default_position
        self._active_category: PoiCategory | None = None
        self._pending_viewport_search: tuple[PoiCategory, TransitMode] | None = None
        self._pending_search_result: PoiSearchResult | None = None
        self._visible_pois: tuple[PointOfInterest, ...] = ()

    @diagnostic_action("search")
    def search(self, category: PoiCategory, transit_mode: TransitMode = TransitMode.ALL) -> None:
        self._search_operation_id = current_operation()
        self._active_category = category
        self._pending_search_result = None
        self._visible_pois = ()

        request_viewport = getattr(self._source, "request_search", None)
        poll_viewport = getattr(self._source, "poll_search_result", None)
        if request_viewport is not None and poll_viewport is not None:
            self._pending_viewport_search = (category, transit_mode)
            request_viewport(category.name.casefold())
            return

        # Compatibility path for headless/non-renderer sources. Runtime ORC uses
        # the renderer viewport path above.
        self._pending_viewport_search = None
        position = self._position_provider()
        if position is None:
            self._pending_search_result = PoiSearchResult(category=category, count=0, south=0.0, west=0.0, north=0.0, east=0.0, pois=())
            return
        pois = self._search_pois(PoiSearchQuery(category=category, bounds=_nearby_bounds(position, _NEARBY_RADIUS_M), limit=_NEARBY_LIMIT, transit_mode=transit_mode))
        if pois is None:
            return
        pois = tuple(poi for poi in pois if _distance_m(position, poi.position) <= _NEARBY_RADIUS_M)
        self._visible_pois = pois
        self._pending_search_result = _result_for(category, pois)

    def poll_selected(self) -> PointOfInterest | None:
        raw = self._source.poll_selected()
        if raw is not None:
            # Result markers carry an id; keep the richer SQLite metadata when
            # a renderer selection reports only the basic map feature fields.
            for poi in self._visible_pois:
                if poi.poi_id == raw.poi_id:
                    return enrich_poi(poi)
            return enrich_poi(self._to_poi(raw))
        poll_click = getattr(self._source, "poll_click", None)
        if poll_click is None:
            return None
        click = poll_click()
        if click is None:
            return None
        self._diagnostics.emit(logging.DEBUG, "selection_resolving", self._search_operation_id)
        if click.marker_index is not None:
            if 0 <= click.marker_index < len(self._visible_pois):
                poi = self._visible_pois[click.marker_index]
                if click.marker_id is None or poi.poi_id == click.marker_id:
                    self._diagnostics.emit(logging.DEBUG, "selected", self._search_operation_id, stage="marker_index")
                    return enrich_poi(poi)
            self._diagnostics.emit(logging.DEBUG, "selection_mismatch", self._search_operation_id, stage="marker_index")
        if click.marker_id is not None:
            for poi in self._visible_pois:
                if poi.poi_id == click.marker_id:
                    self._diagnostics.emit(logging.DEBUG, "selected", self._search_operation_id, stage="marker_id")
                    return enrich_poi(poi)
            self._diagnostics.emit(logging.DEBUG, "selection_mismatch", self._search_operation_id, stage="marker_id")
        nearest: PointOfInterest | None = None
        nearest_distance_m = click.selection_radius_m
        for poi in self._visible_pois:
            distance_m = _distance_m(click.position, poi.position)
            if distance_m <= nearest_distance_m:
                nearest = poi
                nearest_distance_m = distance_m
        if nearest is None:
            self._diagnostics.emit(logging.DEBUG, "selection_missed", self._search_operation_id)
            return None
        self._diagnostics.emit(logging.DEBUG, "selected", self._search_operation_id, stage="nearest")
        return enrich_poi(nearest)

    def poll_camera_state(self):
        poll = getattr(self._source, "poll_camera_state", None)
        return poll() if poll is not None else None

    def poll_camera_interaction(self) -> bool:
        poll_camera = getattr(self._source, "poll_camera_interaction", None)
        return bool(poll_camera is not None and poll_camera())

    def poll_search_result(self) -> PoiSearchResult | None:
        poll_viewport = getattr(self._source, "poll_search_result", None)
        if poll_viewport is not None:
            viewport = poll_viewport()
            if viewport is not None:
                pending = self._pending_viewport_search
                if pending is not None and viewport.category == pending[0].name.casefold():
                    category, transit_mode = pending
                    self._pending_viewport_search = None
                    pois = self._search_pois(
                        PoiSearchQuery(
                            category=category,
                            bounds=PoiSearchBounds(
                                south=viewport.south,
                                west=viewport.west,
                                north=viewport.north,
                                east=viewport.east,
                            ),
                            limit=_NEARBY_LIMIT,
                            transit_mode=transit_mode,
                        )
                    )
                    if pois is None:
                        result, self._pending_search_result = self._pending_search_result, None
                        return result
                    self._diagnostics.emit(logging.INFO, "search.completed",
                                           self._search_operation_id, category=category.name.casefold(),
                                           result_count=len(pois))
                    self._visible_pois = pois
                    self._pending_search_result = _result_for(category, pois)
                else:
                    self._diagnostics.emit(logging.DEBUG, "result_discarded", self._search_operation_id)
                # Replies arriving after clear(), or from an older category, are
                # deliberately consumed and discarded instead of redrawing POIs.

        result, self._pending_search_result = self._pending_search_result, None
        return result

    def clear(self) -> None:
        self._active_category = None
        self._pending_viewport_search = None
        self._pending_search_result = None
        self._visible_pois = ()
        self._source.clear()

    def close(self) -> None:
        self._source.close()
        if self._search_source is not None and self._owns_search_source:
            self._search_source.close()
            self._search_source = None

    def _search_pois(self, query: PoiSearchQuery) -> tuple[PointOfInterest, ...] | None:
        try:
            result = self._offline_source().search(query)
            self._diagnostics.succeeded("database", self._search_operation_id)
            return result
        except (sqlite3.Error, OSError) as error:
            self._diagnostics.failed("database", error, self._search_operation_id)
            self._visible_pois = ()
            self._pending_search_result = PoiSearchResult(
                category=query.category, count=0, south=0, west=0, north=0, east=0,
                error="POI search unavailable: check the installed offline search database",
            )
            return None

    def _offline_source(self) -> PoiSearchSourceIf:
        if self._search_source is None:
            database = search_database_path()
            self._diagnostics.emit(logging.DEBUG, "index_opening", self._search_operation_id)
            self._search_source = SqlitePoiSearchSource(database)
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
    haversine = (math.sin(dlat / 2.0) ** 2 + math.cos(first.latitude_rad) * math.cos(second.latitude_rad) * math.sin(dlon / 2.0) ** 2)
    return 2.0 * _EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(haversine)))
