# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Canonical business metadata loaded from the OpenRoadCode business catalog."""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

_CATALOG_PATH = Path(__file__).with_name("businesses.toml")


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


def _load_businesses(path: Path = _CATALOG_PATH) -> tuple[BusinessEntity, ...]:
    with path.open("rb") as stream:
        document = tomllib.load(stream)

    businesses: list[BusinessEntity] = []
    for provider_id, raw in document.get("business", {}).items():
        businesses.append(
            BusinessEntity(
                provider_id=provider_id,
                brand=str(raw["name"]),
                aliases=tuple(str(alias) for alias in raw.get("aliases", ())),
                categories=frozenset(str(value).casefold() for value in raw.get("categories", ())),
                capabilities=frozenset(str(value).casefold() for value in raw.get("capabilities", ())),
            )
        )
    return tuple(businesses)


BUSINESSES = _load_businesses()

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
