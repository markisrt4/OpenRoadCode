# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Canonical business metadata loaded from OpenRoadCode catalog data."""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

_CATALOG_DIR = Path(__file__).with_name("catalog") / "businesses"


@dataclass(frozen=True, slots=True)
class BusinessEntity:
    """Platform-neutral identity and capabilities for a known business brand."""

    provider_id: str
    brand: str
    aliases: tuple[str, ...]
    categories: frozenset[str]
    capabilities: frozenset[str]
    wikidata: tuple[str, ...] = ()


def _normalize(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def _load_businesses(directory: Path = _CATALOG_DIR) -> tuple[BusinessEntity, ...]:
    businesses: dict[str, BusinessEntity] = {}

    for path in sorted(directory.glob("*.toml")):
        with path.open("rb") as stream:
            document = tomllib.load(stream)

        for provider_id, raw in document.get("business", {}).items():
            if provider_id in businesses:
                raise ValueError(f"Duplicate business provider_id {provider_id!r} in {path}")
            businesses[provider_id] = BusinessEntity(
                provider_id=provider_id,
                brand=str(raw["name"]),
                aliases=tuple(str(alias) for alias in raw.get("aliases", ())),
                categories=frozenset(
                    str(value).casefold() for value in raw.get("categories", ())
                ),
                capabilities=frozenset(
                    str(value).casefold() for value in raw.get("capabilities", ())
                ),
                wikidata=tuple(str(value).strip().upper() for value in raw.get("wikidata", ())),
            )

    return tuple(businesses.values())


BUSINESSES = _load_businesses()

_ALIAS_INDEX = {
    _normalize(alias): business
    for business in BUSINESSES
    for alias in (business.brand, *business.aliases)
}

_WIKIDATA_INDEX = {
    identifier: business
    for business in BUSINESSES
    for identifier in business.wikidata
}


def resolve_business(
    *, brand: str | None = None, name: str | None = None,
    brand_wikidata: str | None = None, operator: str | None = None,
) -> BusinessEntity | None:
    """Prefer structured brand identity, then exact brand/operator/name aliases."""
    for identifier in (brand_wikidata or '').split(';'):
        match = _WIKIDATA_INDEX.get(identifier.strip().upper())
        if match is not None:
            return match
    for candidate in (brand, operator, name):
        match = _ALIAS_INDEX.get(_normalize(candidate))
        if match is not None:
            return match
    return None
