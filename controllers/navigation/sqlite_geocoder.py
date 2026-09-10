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

_STREET_SUFFIXES = {
    "st": "street",
    "rd": "road",
    "ave": "avenue",
    "av": "avenue",
    "blvd": "boulevard",
    "dr": "drive",
    "ln": "lane",
    "ct": "court",
    "cir": "circle",
    "trl": "trail",
    "ter": "terrace",
    "pkwy": "parkway",
    "pl": "place",
    "hwy": "highway",
}


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
        rows = self._connection.execute(
            """
            SELECT house_number, street, unit, city, state, postcode, country,
                   latitude, longitude
            FROM address
            WHERE house_number = ? COLLATE NOCASE
            ORDER BY id
            LIMIT 500
            """,
            (query.house_number,),
        ).fetchall()

        requested_street = _normalize_street(query.street)
        postcode_center = self._postcode_center(query.postcode)
        ranked: list[tuple[int, float, sqlite3.Row]] = []
        for row in rows:
            candidate_street = _normalize_street(str(row["street"] or ""))
            if not candidate_street:
                continue

            score = 0
            if candidate_street == requested_street:
                score += 100
            elif requested_street.startswith(candidate_street + " "):
                score += 90
            elif candidate_street.startswith(requested_street + " "):
                score += 80
            else:
                continue

            if query.city and row["city"] and _normalize_words(str(row["city"])) == _normalize_words(query.city):
                score += 10
            if query.state and row["state"] and str(row["state"]).casefold() == query.state.casefold():
                score += 5
            if query.postcode and row["postcode"] and str(row["postcode"]).casefold() == query.postcode.casefold():
                score += 5
            ranked.append((score, row))

        ranked.sort(key=lambda item: (-item[0], str(item[1]["street"]).casefold()))
        return [
            GeocodeResult(
                display_name=_format_address(row),
                position=_point(row),
                confidence=min(1.0, 0.75 + score / 400.0),
                source="address",
            )
            for score, row in ranked[:limit]
        ]

    def _postcode_center(self, postcode: str | None) -> tuple[float, float] | None:
        if not postcode:
            return None
        row = self._connection.execute(
            """
            SELECT AVG(latitude) AS latitude, AVG(longitude) AS longitude
            FROM address
            WHERE postcode = ?
            """,
            (postcode,),
        ).fetchone()
        if row is None or row["latitude"] is None or row["longitude"] is None:
            return None
        return float(row["latitude"]), float(row["longitude"])

    def _street_results(self, query: _ParsedQuery, limit: int) -> list[GeocodeResult]:
        if not query.street:
            return []

        requested = _normalize_street(query.street)
        search_tokens = [token for token in query.street.split() if token]
        search_token = next(
            (
                token
                for token in search_tokens
                if token.casefold().rstrip(".") not in {"east", "west", "north", "south", "e", "w", "n", "s"}
            ),
            search_tokens[0],
        )
        rows = self._connection.execute(
            """
            SELECT name, city, state, postcode, latitude, longitude
            FROM street
            WHERE name LIKE ? COLLATE NOCASE
            ORDER BY id
            LIMIT 1000
            """,
            (f"%{search_token}%",),
        ).fetchall()

        postcode_center = self._postcode_center(query.postcode)
        ranked: list[tuple[int, float, sqlite3.Row]] = []
        for row in rows:
            candidate = _normalize_street(str(row["name"] or ""))
            if not candidate:
                continue
            score = 0
            if candidate == requested:
                score += 100
            elif candidate.startswith(requested + " ") or requested.startswith(candidate + " "):
                score += 80
            else:
                continue

            if query.city and row["city"] and _normalize_words(str(row["city"])) == _normalize_words(query.city):
                score += 10
            if query.state and row["state"] and str(row["state"]).casefold() == query.state.casefold():
                score += 5
            if query.postcode and row["postcode"] and str(row["postcode"]).casefold() == query.postcode.casefold():
                score += 5

            distance_km = float("inf")
            if postcode_center is not None:
                distance_km = _distance_km(
                    postcode_center[0],
                    postcode_center[1],
                    float(row["latitude"]),
                    float(row["longitude"]),
                )
            ranked.append((score, distance_km, row))

        ranked.sort(key=lambda item: (-item[0], item[1], str(item[2]["name"]).casefold()))
        return [
            GeocodeResult(
                display_name=_format_street(row),
                position=_point(row),
                confidence=0.55 if query.house_number else 0.8,
                source="street",
            )
            for _, _, row in ranked[:limit]
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


def _normalize_words(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.casefold()))


def _normalize_street(value: str) -> str:
    words = re.findall(r"[a-z0-9]+", value.casefold())
    if words:
        words[-1] = _STREET_SUFFIXES.get(words[-1], words[-1])
    return " ".join(words)


def _parse_query(value: str) -> _ParsedQuery:
    match = _ADDRESS_RE.match(value)
    assert match is not None
    first = match.group(1).strip()
    remainder = (match.group(2) or "").strip()

    street_match = _STREET_RE.match(first)
    house_number = street_match.group(1).strip() if street_match else None
    street = street_match.group(2).strip() if street_match else first

    city = None
    state = None
    postcode = None

    if remainder:
        parts = [part.strip() for part in remainder.split(",") if part.strip()]
        city = parts[0] if parts else None
        if len(parts) >= 2:
            state_tokens = parts[1].split()
            if state_tokens:
                state = state_tokens[0]
            if len(state_tokens) > 1:
                postcode = state_tokens[1]
    elif house_number is not None:
        tokens = street.split()

        if tokens and re.fullmatch(r"[0-9]{5}(?:-[0-9]{4})?", tokens[-1]):
            postcode = tokens[-1]
            tokens = tokens[:-1]

        if tokens and re.fullmatch(r"[A-Za-z]{2}", tokens[-1]):
            state = tokens[-1]
            tokens = tokens[:-1]

        street_suffix_index = _find_street_suffix_index(tokens)
        if street_suffix_index is not None:
            street = " ".join(tokens[: street_suffix_index + 1])
            locality_tokens = tokens[street_suffix_index + 1 :]
            city = " ".join(locality_tokens) or None

    return _ParsedQuery(house_number, street, city, state, postcode)


def _find_street_suffix_index(tokens: list[str]) -> int | None:
    suffixes = set(_STREET_SUFFIXES) | set(_STREET_SUFFIXES.values())
    for index, token in enumerate(tokens):
        if token.casefold().rstrip(".") in suffixes:
            return index
    return None

def _distance_km(lat1_deg: float, lon1_deg: float, lat2_deg: float, lon2_deg: float) -> float:
    lat1 = math.radians(lat1_deg)
    lon1 = math.radians(lon1_deg)
    lat2 = math.radians(lat2_deg)
    lon2 = math.radians(lon2_deg)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    haversine = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2.0) ** 2
    )
    return 2.0 * 6371.0088 * math.asin(min(1.0, math.sqrt(haversine)))


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
