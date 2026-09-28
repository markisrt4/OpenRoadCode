# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for offline search-index validation."""

import sqlite3

import pytest

from tools.map_builder.builder.validate import (
    ValidationError,
    validate_search_index,
)


def _create_poi_database(path, *, include_transit_mode: bool) -> None:
    transit_column = ", transit_mode TEXT" if include_transit_mode else ""

    with sqlite3.connect(path) as db:
        db.execute(
            f"""
            CREATE TABLE poi (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                brand TEXT,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                category TEXT NOT NULL,
                class TEXT,
                subclass TEXT
                {transit_column}
            )
            """
        )


def test_validate_search_index_accepts_current_poi_schema(tmp_path) -> None:
    database = tmp_path / "openroadcode-search.sqlite"
    _create_poi_database(database, include_transit_mode=True)

    result = validate_search_index(database)

    assert "poi" in result["tables"]
    assert "transit_mode" in result["poi_columns"]


def test_validate_search_index_rejects_legacy_poi_schema(tmp_path) -> None:
    database = tmp_path / "openroadcode-search.sqlite"
    _create_poi_database(database, include_transit_mode=False)

    with pytest.raises(
        ValidationError,
        match=r"missing required column\(s\): transit_mode",
    ):
        validate_search_index(database)

