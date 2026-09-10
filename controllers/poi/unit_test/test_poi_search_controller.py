# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

import math

from controllers.poi import (
    PoiActionKind,
    PoiCategory,
    PoiSearchBounds,
    PoiSearchController,
    PoiSearchQuery,
    PointOfInterest,
)
from protocols.map_renderer.map_poi_source import RawMapPoi
from ui.navigation import GeoPoint


class FakeMapPoiSource:
    def __init__(self, selected: RawMapPoi | None = None) -> None:
        self.selected = selected
        self.cleared = False
        self.closed = False

    def poll_selected(self) -> RawMapPoi | None:
        selected, self.selected = self.selected, None
        return selected

    def clear(self) -> None:
        self.cleared = True

    def close(self) -> None:
        self.closed = True


class FakeSearchSource:
    def __init__(self, results: tuple[PointOfInterest, ...] = ()) -> None:
        self.results = results
        self.queries: list[PoiSearchQuery] = []
        self.closed = False

    def search(self, query: PoiSearchQuery) -> tuple[PointOfInterest, ...]:
        self.queries.append(query)
        return self.results

    def close(self) -> None:
        self.closed = True


def _position() -> GeoPoint:
    return GeoPoint(math.radians(42.80), math.radians(-83.01))


def test_search_uses_offline_source_near_current_position() -> None:
    result_poi = PointOfInterest(
        poi_id="fuel-1",
        name="Fuel",
        category=PoiCategory.FUEL,
        position=GeoPoint(math.radians(42.81), math.radians(-83.02)),
    )
    map_source = FakeMapPoiSource()
    search_source = FakeSearchSource((result_poi,))
    controller = PoiSearchController(
        map_source,  # type: ignore[arg-type]
        search_source=search_source,
        position_provider=_position,
    )

    controller.search(PoiCategory.FUEL)

    assert len(search_source.queries) == 1
    query = search_source.queries[0]
    assert query.category is PoiCategory.FUEL
    assert query.bounds.south < 42.80 < query.bounds.north
    assert query.bounds.west < -83.01 < query.bounds.east

    result = controller.poll_search_result()
    assert result is not None
    assert result.category is PoiCategory.FUEL
    assert result.count == 1
    assert math.isclose(result.south, 42.81)
    assert math.isclose(result.west, -83.02)


def test_search_without_position_returns_empty_result() -> None:
    search_source = FakeSearchSource()
    controller = PoiSearchController(
        FakeMapPoiSource(),  # type: ignore[arg-type]
        search_source=search_source,
        position_provider=lambda: None,
    )

    controller.search(PoiCategory.FOOD)

    assert search_source.queries == []
    result = controller.poll_search_result()
    assert result is not None
    assert result.category is PoiCategory.FOOD
    assert result.count == 0


def test_nearby_search_bounds_are_reasonably_local() -> None:
    search_source = FakeSearchSource()
    controller = PoiSearchController(
        FakeMapPoiSource(),  # type: ignore[arg-type]
        search_source=search_source,
        position_provider=_position,
    )

    controller.search(PoiCategory.GROCERY)

    query = search_source.queries[0]
    assert isinstance(query.bounds, PoiSearchBounds)
    assert 42.6 < query.bounds.south < 42.8
    assert 42.8 < query.bounds.north < 43.0
    assert -83.3 < query.bounds.west < -83.01
    assert -83.01 < query.bounds.east < -82.7


def test_selected_restaurant_is_enriched_with_order_action() -> None:
    source = FakeMapPoiSource(
        RawMapPoi(
            poi_id="poi-1",
            name="Panera Bread",
            position=GeoPoint(math.radians(42.8), math.radians(-83.0)),
            source_class="restaurant",
        )
    )
    controller = PoiSearchController(
        source,  # type: ignore[arg-type]
        search_source=FakeSearchSource(),
        position_provider=_position,
    )
    poi = controller.poll_selected()
    assert poi is not None
    assert poi.category is PoiCategory.FOOD
    order = next(action for action in poi.actions if action.label == "ORDER")
    assert order.kind is PoiActionKind.ORDER
    assert order.provider_id == "panera"
    assert order.uri is None


def test_fuel_subclass_is_classified_as_fuel() -> None:
    source = FakeMapPoiSource(
        RawMapPoi(
            poi_id="poi-2",
            name="Fuel Stop",
            position=GeoPoint(0.0, 0.0),
            source_class="shop",
            source_subclass="fuel",
        )
    )
    controller = PoiSearchController(
        source,  # type: ignore[arg-type]
        search_source=FakeSearchSource(),
        position_provider=_position,
    )
    poi = controller.poll_selected()
    assert poi is not None
    assert poi.category is PoiCategory.FUEL


def test_search_excludes_pois_outside_true_nearby_radius() -> None:
    outside_circle = PointOfInterest(
        poi_id="corner",
        name="Bounding Box Corner",
        category=PoiCategory.FOOD,
        position=GeoPoint(math.radians(42.97), math.radians(-82.79)),
    )
    search_source = FakeSearchSource((outside_circle,))
    controller = PoiSearchController(
        FakeMapPoiSource(),  # type: ignore[arg-type]
        search_source=search_source,
        position_provider=_position,
    )

    controller.search(PoiCategory.FOOD)

    result = controller.poll_search_result()
    assert result is not None
    assert result.count == 0
