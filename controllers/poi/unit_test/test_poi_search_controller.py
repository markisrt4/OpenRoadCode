# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

import math

from controllers.poi import PoiActionKind, PoiCategory, PoiSearchController
from protocols.map_renderer.map_poi_source import RawMapPoi
from ui.navigation import GeoPoint


class FakePoiSource:
    def __init__(self, selected: RawMapPoi | None = None) -> None:
        self.selected = selected
        self.searches: list[str] = []
        self.cleared = False
        self.closed = False

    def request_search(self, category: str) -> None:
        self.searches.append(category)

    def poll_selected(self) -> RawMapPoi | None:
        selected, self.selected = self.selected, None
        return selected

    def clear(self) -> None:
        self.cleared = True

    def close(self) -> None:
        self.closed = True


def test_search_forwards_semantic_category() -> None:
    source = FakePoiSource()
    controller = PoiSearchController(source)  # type: ignore[arg-type]
    controller.search(PoiCategory.FOOD)
    assert source.searches == ["food"]


def test_selected_restaurant_is_enriched_with_order_action() -> None:
    source = FakePoiSource(
        RawMapPoi(
            poi_id="poi-1",
            name="Panera Bread",
            position=GeoPoint(math.radians(42.8), math.radians(-83.0)),
            source_class="restaurant",
        )
    )
    controller = PoiSearchController(source)  # type: ignore[arg-type]
    poi = controller.poll_selected()
    assert poi is not None
    assert poi.category is PoiCategory.FOOD
    order = next(action for action in poi.actions if action.label == "ORDER")
    assert order.kind is PoiActionKind.OPEN_URI
    assert order.uri is not None
    assert "panerabread.com" in order.uri


def test_fuel_subclass_is_classified_as_fuel() -> None:
    source = FakePoiSource(
        RawMapPoi(
            poi_id="poi-2",
            name="Fuel Stop",
            position=GeoPoint(0.0, 0.0),
            source_class="shop",
            source_subclass="fuel",
        )
    )
    controller = PoiSearchController(source)  # type: ignore[arg-type]
    poi = controller.poll_selected()
    assert poi is not None
    assert poi.category is PoiCategory.FUEL
