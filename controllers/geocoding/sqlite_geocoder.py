# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Offline geocoder backed by the OpenRoadCode search database."""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path

from .geocoder_if import GeocodedLocation


_ADDRESS_RE = re.compile(r"^\s*(?P<number>\S+)\s+(?P<street>[^,]+?)(?:\s*,\s*(?P<city>[^,]+))?(?:\s*,\s*(?P<state>[^,]+))?\s*$")


class SqliteGeocoder:
    def __init__(self, database: str | Path) -> None:
        self._database = Path(database)

    def geocode(self, address: str) -> GeocodedLocation | None:
        query = address.strip()
        if not query:
            return None

        match = _ADDRESS_RE.match(query)
        if match:
            result = self._find_address(
                match.group("number"), match.group("street"),
                match.group("city"), match.group("state"),
            )
            if result is not None:
                return result
        return self._find_place(query)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(f"file:{self._database}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        return connection

    def _find_address(self, number: str, street: str, city: str | None, state: str | None) -> GeocodedLocation | None:
        clauses = ["house_number = ? COLLATE NOCASE", "street = ? COLLATE NOCASE"]
        values: list[str] = [number.strip(), street.strip()]
        if city:
            clauses.append("city = ? COLLATE NOCASE"); values.append(city.strip())
        if state:
            clauses.append("state = ? COLLATE NOCASE"); values.append(state.strip())
        sql = "SELECT * FROM address WHERE " + " AND ".join(clauses) + " LIMIT 1"
        with self._connect() as connection:
            row = connection.execute(sql, values).fetchone()
        if row is None:
            return None
        parts = [f"{row['house_number']} {row['street']}", row['city'], row['state'], row['postcode']]
        return GeocodedLocation(
            formatted_address=", ".join(str(part) for part in parts if part),
            latitude_deg=float(row["latitude"]), longitude_deg=float(row["longitude"]),
        )

    def _find_place(self, query: str) -> GeocodedLocation | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM place WHERE name = ? COLLATE NOCASE "
                "ORDER BY CASE kind WHEN 'city' THEN 0 WHEN 'town' THEN 1 WHEN 'village' THEN 2 ELSE 3 END LIMIT 1",
                (query,),
            ).fetchone()
        if row is None:
            return None
        parts = [row["name"], row["state"], row["country"]]
        return GeocodedLocation(
            formatted_address=", ".join(str(part) for part in parts if part),
            latitude_deg=float(row["latitude"]), longitude_deg=float(row["longitude"]),
        )
