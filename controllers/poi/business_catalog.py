# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Canonical business metadata used to correlate generic map POIs with providers."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BusinessEntity:
    """Platform-neutral identity and capabilities for a known business brand."""

    provider_id: str
    brand: str
    aliases: tuple[str, ...]
    capabilities: frozenset[str]


def _normalize(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


BUSINESSES: tuple[BusinessEntity, ...] = (
    BusinessEntity(
        provider_id="panera",
        brand="Panera Bread",
        aliases=("Panera", "Panera Bread", "Saint Louis Bread Co", "St Louis Bread Co"),
        capabilities=frozenset({"order"}),
    ),
    BusinessEntity(
        provider_id="mcdonalds",
        brand="McDonald's",
        aliases=("McDonald's", "McDonalds", "Mc Donalds"),
        capabilities=frozenset({"order"}),
    ),
)

_ALIAS_INDEX = {
    _normalize(alias): business
    for business in BUSINESSES
    for alias in (business.brand, *business.aliases)
}


def resolve_business(*, brand: str | None = None, name: str | None = None) -> BusinessEntity | None:
    """Resolve a canonical business, preferring explicit brand metadata."""
    for candidate in (brand, name):
        match = _ALIAS_INDEX.get(_normalize(candidate))
        if match is not None:
            return match
    return None
