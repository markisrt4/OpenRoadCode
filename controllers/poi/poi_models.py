# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Renderer-independent point-of-interest value objects."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from ui.navigation import GeoPoint


class PoiCategory(Enum):
    """Semantic POI categories understood by OpenRoadCode."""

    FOOD = auto()
    FUEL = auto()
    GROCERY = auto()
    TRANSIT = auto()
    OTHER = auto()


class PoiActionKind(Enum):
    """Semantic actions that can be offered for a POI."""

    NAVIGATE = auto()
    OPEN_URI = auto()


@dataclass(frozen=True, slots=True)
class PoiAction:
    """Describe an action without prescribing how a platform executes it."""

    kind: PoiActionKind
    label: str
    uri: str | None = None


@dataclass(frozen=True, slots=True)
class PointOfInterest:
    """Describe a selected or discovered place independently of its renderer."""

    poi_id: str
    name: str
    category: PoiCategory
    position: GeoPoint
    brand: str | None = None
    source_class: str | None = None
    source_subclass: str | None = None
    actions: tuple[PoiAction, ...] = ()


@dataclass(frozen=True, slots=True)
class PoiSearchResult:
    """Describe the geographic result of a semantic POI search."""

    category: PoiCategory
    count: int
    south: float
    west: float
    north: float
    east: float
