# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Offline geocoding using the OpenRoadCode search SQLite database."""

from __future__ import annotations

import math
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from controllers.navigation.geocoding_models import GeocodeResult
from ui.navigation import GeoPoint


_ADDRESS_RE = re.compile(r"^\s*([^,]+?)(?:\s*,\s*(.*))?$")
_STREET_RE = re.compile(r"^\s*([0-9]+[A-Za-z0-9-]*)\s+(.+?)\s*$")


@dataclass(frozen=True, slots=True)
class _ParsedQuery:
    house_number: str | None
    street: str
    city: str | None
    state: str | None
    postcode: str | None


class SqliteGeocoder:
    """Resolve addresses, streets, and places from the offline search database."""

    def __init__(self, database: str | Path) -> None:
        self._connection = sqlite3.connect(f"file:{Path(database)}?mode=ro", uri=True)
        self._connection.row_factory = sqlite3.Row

    def close(self) -> None:
        self._connection.close()

    def geocode(self, query: str, *, limit: int = 5) -> tuple[GeocodeResult, ...]:
        normalized = query.strip()
        if not normalized:
            return ()
        if limit < 1:
            raise ValueError("limit must be positive")

        parsed = _parse_query(normalized)
        results: list[GeocodeResult] = []
        if parsed.house_number is not None:
            results.extend(self._address_results(parsed, limit))
        if len(results) < limit:
            results.extend(self._street_results(parsed, limit - len(results)))
        if len(results) < limit:
            results.extend(self._place_results(normalized, limit - len(results)))
        return _dedupe(results)[:limit]

    def _address_results(self, query: _ParsedQuery, limit: int) -> list[GeocodeResult]:
        clauses = [
            "house_number = ? COLLATE NOCASE",
            "street = ? COLLATE NOCASE",
        ]
        params: list[object] = [query.house_number, query.street]

        if query.city:
            clauses.append("(city IS NULL OR city = ? COLLATE NOCASE)")
            params.append(query.city)
        if query.state:
            clauses.append("(state IS NULL OR state = ? COLLATE NOCASE)")
            params.append(query.state)
        if query.postcode:
            clauses.append("(postcode IS NULL OR postcode = ?)")
            params.append(query.postcode)

        params.append(limit)
        rows = self._connection.execute(
            f"""
            SELECT house_number, street, unit, city, state, postcode, country,
                   latitude, longitude
            FROM address
            WHERE {" AND ".join(clauses)}
            ORDER BY
                CASE WHEN city = ? COLLATE NOCASE THEN 0 ELSE 1 END,
                CASE WHEN state = ? COLLATE NOCASE THEN 0 ELSE 1 END,
                id
            LIMIT ?
            """,
            [*params[:-1], query.city or "", query.state or "", params[-1]],
        ).fetchall()

        return [
            GeocodeResult(
                display_name=_format_address(row),
                position=_point(row),
                confidence=1.0,
                source="address",
            )
            for row in rows
        ]

    def _street_results(self, query: _ParsedQuery, limit: int) -> list[GeocodeResult]:
        if not query.street:
            return []
        clauses = ["name = ? COLLATE NOCASE"]
        params: list[object] = [query.street]
        if query.city:
            clauses.append("(city IS NULL OR city = ? COLLATE NOCASE)")
            params.append(query.city)
        if query.state:
            clauses.append("(state IS NULL OR state = ? COLLATE NOCASE)")
            params.append(query.state)
        params.append(limit)
        rows = self._connection.execute(
            f"""
            SELECT name, city, state, postcode, latitude, longitude
            FROM street
            WHERE {" AND ".join(clauses)}
            ORDER BY id
            LIMIT ?
            """,
            params,
        ).fetchall()
        return [
            GeocodeResult(
                display_name=_format_street(row),
                position=_point(row),
                confidence=0.65 if query.house_number else 0.8,
                source="street",
            )
            for row in rows
        ]

    def _place_results(self, query: str, limit: int) -> list[GeocodeResult]:
        rows = self._connection.execute(
            """
            SELECT name, kind, state, country, latitude, longitude
            FROM place
            WHERE name = ? COLLATE NOCASE
            ORDER BY
                CASE kind
                    WHEN 'city' THEN 0
                    WHEN 'town' THEN 1
                    WHEN 'village' THEN 2
                    WHEN 'hamlet' THEN 3
                    ELSE 4
                END,
                id
            LIMIT ?
            """,
            (query, limit),
        ).fetchall()
        return [
            GeocodeResult(
                display_name=_format_place(row),
                position=_point(row),
                confidence=0.7,
                source="place",
            )
            for row in rows
        ]


def _parse_query(value: str) -> _ParsedQuery:
    match = _ADDRESS_RE.match(value)
    assert match is not None
    first = match.group(1).strip()
    remainder = (match.group(2) or "").strip()

    street_match = _STREET_RE.match(first)
    house_number = street_match.group(1).strip() if street_match else None
    street = street_match.group(2).strip() if street_match else first

    parts = [part.strip() for part in remainder.split(",") if part.strip()]
    city = parts[0] if parts else None
    state = None
    postcode = None

    if len(parts) >= 2:
        tokens = parts[1].split()
        if tokens:
            state = tokens[0]
        if len(tokens) > 1:
            postcode = tokens[1]
    elif len(parts) == 1:
        tokens = parts[0].split()
        if len(tokens) >= 2 and re.fullmatch(r"[A-Za-z]{2}", tokens[-2]):
            city = " ".join(tokens[:-2]) or None
            state = tokens[-2]
            postcode = tokens[-1] if re.fullmatch(r"[0-9A-Za-z -]+", tokens[-1]) else None

    return _ParsedQuery(house_number, street, city, state, postcode)


def _point(row: sqlite3.Row) -> GeoPoint:
    return GeoPoint(
        latitude_rad=math.radians(float(row["latitude"])),
        longitude_rad=math.radians(float(row["longitude"])),
    )


def _format_address(row: sqlite3.Row) -> str:
    first = f"{row['house_number']} {row['street']}".strip()
    if row["unit"]:
        first += f" #{row['unit']}"
    return ", ".join(
        str(value) for value in (first, row["city"], row["state"], row["postcode"], row["country"])
        if value
    )


def _format_street(row: sqlite3.Row) -> str:
    return ", ".join(
        str(value) for value in (row["name"], row["city"], row["state"], row["postcode"])
        if value
    )


def _format_place(row: sqlite3.Row) -> str:
    return ", ".join(
        str(value) for value in (row["name"], row["state"], row["country"])
        if value
    )


def _dedupe(results: list[GeocodeResult]) -> tuple[GeocodeResult, ...]:
    seen: set[tuple[str, int, int]] = set()
    unique: list[GeocodeResult] = []
    for result in results:
        key = (
            result.display_name.casefold(),
            round(math.degrees(result.position.latitude_rad) * 1_000_000),
            round(math.degrees(result.position.longitude_rad) * 1_000_000),
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(result)
    return tuple(unique)
