# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Canonical business metadata loaded from OpenRoadCode catalog data."""

from __future__ import annotations

import re
import json
import tomllib
import unicodedata
from urllib.parse import urlsplit
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
    domains: tuple[str, ...] = ()
    icon_id: str | None = None


def _normalize(value: str | None) -> str:
    if not value:
        return ""
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode()
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def _load_businesses(directory: Path = _CATALOG_DIR) -> tuple[BusinessEntity, ...]:
    businesses: dict[str, BusinessEntity] = {}

    generated = directory.parent / 'brands.json'
    if generated.exists():
        document = json.loads(generated.read_text())
        if document.get('schema_version') != 1:
            raise ValueError('Unsupported brand registry schema')
        for provider_id, raw in document['businesses'].items():
            businesses[provider_id] = BusinessEntity(provider_id, raw['name'], tuple(raw['aliases']),
                frozenset(raw['categories']), frozenset(), tuple(raw['wikidata']),
                tuple(raw.get('domains', [])), raw.get('icon_id'))

    manual_ids = set()
    for path in sorted(directory.glob("*.toml")):
        with path.open("rb") as stream:
            document = tomllib.load(stream)

        for provider_id, raw in document.get("business", {}).items():
            if provider_id in manual_ids:
                raise ValueError(f"Duplicate business provider_id {provider_id!r} in {path}")
            manual_ids.add(provider_id)
            original = businesses.get(provider_id)
            businesses[provider_id] = BusinessEntity(
                provider_id=provider_id,
                brand=str(raw["name"]),
                aliases=tuple(sorted(set(str(alias) for alias in raw.get("aliases", ()))
                                     | set(original.aliases if original else ()))),
                categories=frozenset(
                    str(value).casefold() for value in raw.get("categories", ())
                ),
                capabilities=frozenset(
                    str(value).casefold() for value in raw.get("capabilities", ())
                ),
                wikidata=tuple(sorted(set(str(value).strip().upper() for value in raw.get("wikidata", ()))
                                      | set(original.wikidata if original else ()))),
                domains=original.domains if original else (),
                icon_id=original.icon_id if original else None,
            )

    return tuple(businesses.values())


BUSINESSES = _load_businesses()

def resolve_business(
    *, brand: str | None = None, name: str | None = None,
    brand_wikidata: str | None = None, operator: str | None = None,
    website: str | None = None, category: str | None = None,
    businesses: tuple[BusinessEntity, ...] = BUSINESSES,
) -> BusinessEntity | None:
    """Resolve exact identities; ambiguous matches never select an app or logo."""
    eligible = tuple(b for b in businesses if not category or category in b.categories)
    identifiers = {value.strip().upper() for value in (brand_wikidata or '').split(';') if value.strip()}
    matches = {b for b in eligible if identifiers.intersection(b.wikidata)}
    if matches:
        return next(iter(matches)) if len(matches) == 1 else None
    try:
        parsed = urlsplit(website or '')
        host = (parsed.hostname or '').casefold().rstrip('.') if parsed.scheme in {'http', 'https'} and not parsed.username else ''
    except ValueError:
        host = ''
    matches = {b for b in eligible if any(host == domain or host.endswith('.' + domain) for domain in b.domains)}
    if matches:
        return next(iter(matches)) if len(matches) == 1 else None
    for candidate in (brand, operator, name):
        normalized = _normalize(candidate)
        matches = {b for b in eligible if normalized and normalized in {_normalize(a) for a in (b.brand, *b.aliases)}}
        if matches:
            return next(iter(matches)) if len(matches) == 1 else None
    return None
