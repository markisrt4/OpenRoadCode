# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Canonical business metadata loaded from OpenRoadCode catalog data."""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

_CATALOG_DIR = Path(__file__).resolve().parents[2] / "data" / "business_catalog" / "businesses"


@dataclass(frozen=True, slots=True)
class BusinessEntity:
    """Platform-neutral identity and capabilities for a known business brand."""

    provider_id: str
    brand: str
    aliases: tuple[str, ...]
    categories: frozenset[str]
    capabilities: frozenset[str]


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
            )

    return tuple(businesses.values())


BUSINESSES = _load_businesses()

_ALIAS_INDEX = {
    _normalize(alias): business
    for business in BUSINESSES
    for alias in (business.brand, *business.aliases)
}


def resolve_business(
    *, brand: str | None = None, name: str | None = None
) -> BusinessEntity | None:
    """Resolve a canonical business, preferring explicit brand metadata."""
    for candidate in (brand, name):
        match = _ALIAS_INDEX.get(_normalize(candidate))
        if match is not None:
            return match
    return None
