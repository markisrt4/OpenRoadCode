# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Restaurant metadata used to enrich generic POIs with ordering actions."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RestaurantDestination:
    brand: str
    aliases: tuple[str, ...]
    android_package: str | None
    order_url: str


def _normalize(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


RESTAURANTS: tuple[RestaurantDestination, ...] = (
    RestaurantDestination(
        brand="Panera Bread",
        aliases=("Panera", "Panera Bread", "Saint Louis Bread Co", "St Louis Bread Co"),
        android_package="com.panera.bread",
        order_url="https://www.panerabread.com/en-us/start-an-order.html",
    ),
    RestaurantDestination(
        brand="McDonald's",
        aliases=("McDonald's", "McDonalds", "Mc Donalds"),
        android_package="com.mcdonalds.app",
        order_url="https://www.mcdonalds.com/us/en-us.html",
    ),
)

_ALIAS_INDEX = {
    _normalize(alias): restaurant
    for restaurant in RESTAURANTS
    for alias in (restaurant.brand, *restaurant.aliases)
}


def resolve_restaurant_poi(
    *, brand: str | None = None, name: str | None = None
) -> RestaurantDestination | None:
    """Resolve restaurant metadata, preferring explicit brand information."""
    for candidate in (brand, name):
        match = _ALIAS_INDEX.get(_normalize(candidate))
        if match is not None:
            return match
    return None
